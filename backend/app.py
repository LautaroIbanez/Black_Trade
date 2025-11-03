"""FastAPI application for Black Trade backend."""
import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
import pandas as pd

from backend.services.market_data_service import MarketDataService
from backtest.engine import BacktestEngine
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
# Data loading now handled by market_data_service
from backend.api.routes.chart import router as chart_router
from backend.api.routes.monitoring import router as monitoring_router
from backend.api.routes.risk import router as risk_router
from backend.api.routes.execution import router as execution_router
from backend.api.routes.observability import router as observability_router
from backend.api.routes.websocket import router as websocket_router
from backend.api.routes.recommendations import router as recommendations_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.recommendation_tracking import router as recommendation_tracking_router
from backend.api.routes.strategies import router as strategies_router
from recommendation.config import TIMEFRAMES_ACTIVE

load_dotenv()

# Configure logging for compliance
from backend.config.logging_config import configure_logging
configure_logging()

logger = logging.getLogger(__name__)

# Initialize observability
from backend.observability.telemetry import init_telemetry
from backend.observability.metrics import get_metrics_collector
from backend.observability.middleware import ObservabilityMiddleware

# Initialize telemetry (OpenTelemetry)
telemetry_manager = init_telemetry(
    service_name="black-trade",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
    enable_tracing=os.getenv("ENABLE_TRACING", "true").lower() == "true",
    enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
)

app = FastAPI(title="Black Trade API", version="1.0.0")

# Add security middleware
from backend.config.middleware_security import SecurityMiddleware, InputSanitizationMiddleware
from backend.middleware.sanitization import SanitizationMiddleware
app.add_middleware(SecurityMiddleware)
app.add_middleware(SanitizationMiddleware)

# Add observability middleware
app.add_middleware(ObservabilityMiddleware)

# Instrument FastAPI
telemetry_manager.instrument_fastapi(app)
telemetry_manager.instrument_requests()
try:
    telemetry_manager.instrument_sqlalchemy()
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
market_data_service = MarketDataService()
backtest_engine = BacktestEngine()

# Cache for results
last_results = {}

class RefreshResponse(BaseModel):
    success: bool
    message: str
    results: Dict[str, Any]

class ContributionBreakdownResponse(BaseModel):
    strategy_name: str
    timeframe: str
    signal: int
    confidence: float
    strength: float
    score: float
    weight: float
    entry_contribution: Dict[str, float]
    sl_contribution: float
    tp_contribution: float
    reason: str

class RecommendationResponse(BaseModel):
    action: str
    confidence: float
    entry_range: Dict[str, float]
    stop_loss: float
    take_profit: float
    current_price: float
    primary_strategy: str
    supporting_strategies: List[str]
    strategy_details: List[Dict[str, Any]]
    signal_consensus: float
    risk_level: str
    contribution_breakdown: Optional[List[ContributionBreakdownResponse]] = None
    # New normalized and transparency fields
    risk_reward_ratio: float = 0.0
    entry_label: str = ""
    risk_percentage: float = 0.0
    normalized_weights_sum: float = 0.0
    # Consolidated position sizing fields
    position_size_usd: float = 0.0
    position_size_pct: float = 0.0

class StrategyMetrics(BaseModel):
    strategy_name: str
    timeframe: str
    total_trades: int
    win_rate: float
    net_pnl: float
    max_drawdown: float
    profit_factor: float
    expectancy: float
    score: float

def initialize_services():
    """Initialize database and services."""
    try:
        # Initialize database
        from backend.db.init_db import initialize_database
        if not initialize_database():
            logger.error("Failed to initialize database")
            return False
        
        # Initialize auth service and default users
        try:
            from backend.auth.permissions import init_auth_service
            init_auth_service()
            # Ensure app-level auth wrapper is initialized
            from backend.services.auth_service import app_auth_service  # noqa: F401
            logger.info("Auth service initialized")
        except Exception as e:
            logger.error(f"Error initializing auth service: {e}")
        
        # Initialize risk system (engine + adapter) and set global API instance
        try:
            from backend.scripts.init_risk_system import init_risk_system
            use_simulated = os.getenv('USE_SIMULATED_RISK', 'true').lower() == 'true'
            init_risk_system(use_simulated=use_simulated)
            logger.info("Risk system initialized")
        except Exception as e:
            logger.error(f"Error initializing risk system: {e}")
        
        # Initialize ingestion scheduler
        from backend.tasks.scheduler import init_scheduler
        scheduler = init_scheduler()
        if scheduler:
            scheduler.start()
            logger.info("Schedulers started")

        # Initialize execution system (engine + coordinator)
        try:
            from backend.scripts.init_execution_system import init_execution_system
            use_sim_exec = os.getenv('USE_SIMULATED_EXECUTION', 'true').lower() == 'true'
            init_execution_system(use_simulated_adapter=use_sim_exec, use_risk_engine=False)
            logger.info("Execution system initialized")
        except Exception as e:
            logger.error(f"Error initializing execution system: {e}")
        
        logger.info("Services initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # Run database initialization synchronously
    initialize_services()
    
    # Start ingestion scheduler asynchronously
    try:
        from backend.tasks.scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            # Start ingestion task
            await scheduler.start_async()
    except Exception as e:
        logger.error(f"Error starting ingestion scheduler: {e}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Black Trade API", "status": "running"}

@app.post("/refresh")
async def refresh_data() -> RefreshResponse:
    """
    Refresh data and run backtests.
    
    NOTE: This endpoint is kept for backward compatibility.
    Data ingestion is now handled automatically by the ingestion pipeline.
    This endpoint only triggers backtests on existing data.
    """
    global last_results
    
    try:
        symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        env_tfs = os.getenv('TIMEFRAMES')
        timeframes = env_tfs.split(',') if env_tfs else TIMEFRAMES_ACTIVE
        
        # Get data summary from database
        logger.info("Checking data availability...")
        data_summary = market_data_service.get_data_summary(symbol, timeframes)
        logger.info(f"Data summary: {data_summary['overall_status']}")
        
        # Note: Data refresh is now handled automatically by ingestion pipeline
        refresh_results = market_data_service.refresh_latest_candles(symbol, timeframes)
        
        # Get enabled strategies from registry
        strategies = strategy_registry.get_enabled_strategies()
        logger.info(f"Running backtests with {len(strategies)} enabled strategies")
        all_results = {}
        
        for timeframe in timeframes:
            try:
                # Load data from database
                data = market_data_service.load_ohlcv_data(symbol, timeframe)
                
                if data.empty:
                    logger.warning(f"No data available for {timeframe}")
                    continue
                
                # Convert timestamp column to datetime for compatibility
                if 'timestamp' in data.columns:
                    data['datetime'] = pd.to_datetime(data['timestamp'], unit='ms')
                
                # Create validation report (simplified)
                validation_report = {
                    'valid': True,
                    'total_candles': len(data),
                    'is_fresh': True,
                }
                
                # Log validation results
                if not validation_report.get("valid", False):
                    logger.warning(f"Data validation issues for {timeframe}: {validation_report}")
                
                results = backtest_engine.run_multiple_backtests(strategies, data, timeframe)
                ranked_results = backtest_engine.rank_strategies(results)
                # Remove heavy/non-serializable fields (e.g., trades) before returning
                for r in ranked_results:
                    if isinstance(r, dict) and 'trades' in r:
                        try:
                            del r['trades']
                        except Exception:
                            pass
                all_results[timeframe] = ranked_results
            except Exception as e:
                logger.error(f"Error processing {timeframe}: {e}")
                continue
        
        last_results = all_results
        
        # Ensure response is JSON serializable
        safe_results = jsonable_encoder(all_results)
        return RefreshResponse(
            success=True,
            message="Data refreshed and backtests completed",
            results=safe_results
        )
        
    except Exception as e:
        logger.error(f"Error in refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendation")
async def get_recommendation(profile: str = "balanced") -> RecommendationResponse:
    """Get current trading recommendation from live snapshots; no manual refresh required."""
    try:
        from backend.recommendation.live_recommendations_service import live_recommendations_service
        symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        env_tfs = os.getenv('TIMEFRAMES')
        timeframes = env_tfs.split(',') if env_tfs else TIMEFRAMES_ACTIVE

        # Prefer cached/live snapshot
        snapshot = live_recommendations_service.get_latest_snapshot(symbol, timeframes)
        if snapshot:
            # Map snapshot dict to RecommendationResponse fields
            return RecommendationResponse(
                action=snapshot.get('action', 'HOLD'),
                confidence=float(snapshot.get('confidence', 0.0)),
                entry_range=snapshot.get('entry_range', {}),
                stop_loss=float(snapshot.get('stop_loss', 0.0)),
                take_profit=float(snapshot.get('take_profit', 0.0)),
                current_price=float(snapshot.get('current_price', 0.0)),
                primary_strategy=snapshot.get('primary_strategy', ''),
                supporting_strategies=snapshot.get('supporting_strategies', []),
                strategy_details=snapshot.get('strategy_details', []),
                signal_consensus=float(snapshot.get('signal_consensus', 0.0)),
                risk_level=snapshot.get('risk_level', 'LOW'),
                contribution_breakdown=None,
                risk_reward_ratio=float(snapshot.get('risk_reward_ratio', 0.0)),
                entry_label=snapshot.get('entry_label', ''),
                risk_percentage=float(snapshot.get('risk_percentage', 0.0)),
                normalized_weights_sum=float(snapshot.get('normalized_weights_sum', 0.0)),
                position_size_usd=float(snapshot.get('position_size_usd', 0.0)),
                position_size_pct=float(snapshot.get('position_size_pct', 0.0)),
            )

        # Fallback: compute on the fly using current DB data
        symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        current_data = {}
        for timeframe in timeframes:
            try:
                data = market_data_service.load_ohlcv_data(symbol, timeframe)
                if not data.empty:
                    current_data[timeframe] = data
            except Exception as e:
                logger.error(f"Error loading data for {timeframe}: {e}")
                continue
        if not current_data:
            raise HTTPException(status_code=404, detail="No current data available.")
        recommendation = recommendation_service.generate_recommendation(current_data, {}, profile)
        return RecommendationResponse(
            action=recommendation.action,
            confidence=recommendation.confidence,
            entry_range=recommendation.entry_range,
            stop_loss=recommendation.stop_loss,
            take_profit=recommendation.take_profit,
            current_price=recommendation.current_price,
            primary_strategy=recommendation.primary_strategy,
            supporting_strategies=recommendation.supporting_strategies,
            strategy_details=recommendation.strategy_details,
            signal_consensus=recommendation.signal_consensus,
            risk_level=recommendation.risk_level,
            contribution_breakdown=None,
            risk_reward_ratio=recommendation.risk_reward_ratio,
            entry_label=recommendation.entry_label,
            risk_percentage=recommendation.risk_percentage,
            normalized_weights_sum=recommendation.normalized_weights_sum,
            position_size_usd=recommendation.position_size_usd,
            position_size_pct=recommendation.position_size_pct
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/strategies")
async def get_strategies() -> Dict[str, Any]:
    """Get strategy metrics for all timeframes."""
    if not last_results:
        raise HTTPException(status_code=404, detail="No results available. Please call /refresh first.")
    
    response = {
        "timeframes": {},
        "summary": {}
    }
    
    for timeframe, results in last_results.items():
        response["timeframes"][timeframe] = results
        if results:
            response["summary"][timeframe] = {
                "top_strategy": results[0]['strategy_name'] if results else None,
                "top_score": results[0].get('score', 0) if results else 0
            }
    
    return response

@app.get("/strategies/info")
async def get_strategies_info() -> Dict[str, Any]:
    """Get information about all strategies."""
    return strategy_registry.get_strategy_info()

@app.get("/strategies/config")
async def get_strategies_config() -> List[Dict[str, Any]]:
    """Get configuration for all strategies."""
    return strategy_registry.list_strategies()

@app.post("/strategies/{strategy_name}/enable")
async def enable_strategy(strategy_name: str) -> Dict[str, Any]:
    """Enable a strategy."""
    success = strategy_registry.enable_strategy(strategy_name)
    if success:
        return {"success": True, "message": f"Strategy {strategy_name} enabled"}
    else:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_name} not found")

@app.post("/strategies/{strategy_name}/disable")
async def disable_strategy(strategy_name: str) -> Dict[str, Any]:
    """Disable a strategy."""
    success = strategy_registry.disable_strategy(strategy_name)
    if success:
        return {"success": True, "message": f"Strategy {strategy_name} disabled"}
    else:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_name} not found")

@app.put("/strategies/{strategy_name}/config")
async def update_strategy_config(strategy_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Update strategy configuration."""
    success = strategy_registry.update_strategy_config(strategy_name, **config)
    if success:
        return {"success": True, "message": f"Strategy {strategy_name} configuration updated"}
    else:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_name} not found")

@app.post("/strategies/reload")
async def reload_strategies() -> Dict[str, Any]:
    """Reload strategy configurations from file."""
    strategy_registry.reload_config()
    return {"success": True, "message": "Strategy configurations reloaded"}

# Include routers
app.include_router(chart_router, prefix="/api", tags=["chart"])
app.include_router(monitoring_router, prefix="/api", tags=["monitoring"])
app.include_router(risk_router, prefix="/api/risk", tags=["risk"])
app.include_router(execution_router, prefix="/api/execution", tags=["execution"])
app.include_router(observability_router, prefix="/api", tags=["observability"])
app.include_router(strategies_router)
app.include_router(recommendations_router)
app.include_router(recommendation_tracking_router)
app.include_router(auth_router)

# WebSocket route
from backend.api.routes.websocket import manager, websocket_endpoint
app.add_websocket_route("/ws", websocket_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
