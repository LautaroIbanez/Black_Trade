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

from data.binance_client import BinanceClient
from data.sync_service import SyncService
from backtest.engine import BacktestEngine
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
from backtest.data_loader import data_loader
from backend.api.routes.chart import router as chart_router
from backend.api.routes.monitoring import router as monitoring_router
from backend.api.routes.risk import router as risk_router
from backend.api.routes.execution import router as execution_router
from backend.api.routes.observability import router as observability_router
from backend.api.routes.websocket import router as websocket_router
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
app.add_middleware(SecurityMiddleware)
app.add_middleware(InputSanitizationMiddleware)

# Add observability middleware
app.add_middleware(ObservabilityMiddleware)

# Instrument FastAPI
telemetry_manager.instrument_fastapi(app)
telemetry_manager.instrument_requests()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
binance_client = None
sync_service = None
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
    """Initialize Binance client and sync service."""
    global binance_client, sync_service
    try:
        binance_client = BinanceClient()
        sync_service = SyncService(binance_client)
        logger.info("Services initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    initialize_services()

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Black Trade API", "status": "running"}

@app.post("/refresh")
async def refresh_data() -> RefreshResponse:
    """Refresh data and run backtests."""
    global last_results
    
    if not binance_client or not sync_service:
        if not initialize_services():
            raise HTTPException(status_code=500, detail="Failed to initialize services")
    
    try:
        symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        env_tfs = os.getenv('TIMEFRAMES')
        timeframes = env_tfs.split(',') if env_tfs else TIMEFRAMES_ACTIVE
        
        # Refresh data
        logger.info("Refreshing data...")
        refresh_results = sync_service.refresh_latest_candles(symbol, timeframes)
        
        # If no data files exist, download initial data
        if not any(refresh_results.values()):
            logger.info("No data files found. Downloading initial historical data...")
            download_results = sync_service.download_historical_data(symbol, timeframes, days_back=365)
            logger.info(f"Downloaded initial data: {download_results}")
        
        # Detect and fill gaps in data
        logger.info("Detecting and filling data gaps...")
        gap_results = sync_service.detect_and_fill_gaps(symbol, timeframes)
        logger.info(f"Gap detection results: {gap_results}")
        
        # Validate data quality
        logger.info("Validating data quality...")
        data_summary = data_loader.get_data_summary(symbol, timeframes)
        logger.info(f"Data quality summary: {data_summary['overall_status']}")
        
        # Get enabled strategies from registry
        strategies = strategy_registry.get_enabled_strategies()
        logger.info(f"Running backtests with {len(strategies)} enabled strategies")
        all_results = {}
        
        for timeframe in timeframes:
            try:
                # Load data with validation
                data, validation_report = data_loader.load_data(
                    symbol, timeframe, validate_continuity=True
                )
                
                if data.empty:
                    logger.warning(f"No data available for {timeframe}")
                    continue
                
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
    """Get current trading recommendation based on real-time signals."""
    if not last_results:
        raise HTTPException(status_code=404, detail="No results available. Please call /refresh first.")
    
    try:
        # Load current data for all timeframes
        symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        env_tfs = os.getenv('TIMEFRAMES')
        timeframes = env_tfs.split(',') if env_tfs else TIMEFRAMES_ACTIVE
        
        current_data = {}
        for timeframe in timeframes:
            try:
                data = sync_service.load_ohlcv_data(symbol, timeframe)
                if not data.empty:
                    current_data[timeframe] = data
            except Exception as e:
                logger.error(f"Error loading data for {timeframe}: {e}")
                continue
        
        if not current_data:
            raise HTTPException(status_code=404, detail="No current data available.")
        
        # Generate recommendation using real-time signals with profile-specific weights
        recommendation = recommendation_service.generate_recommendation(current_data, last_results, profile)
        
        # Convert contribution breakdown to response format
        contribution_breakdown = None
        if recommendation.contribution_breakdown:
            contribution_breakdown = [
                ContributionBreakdownResponse(
                    strategy_name=cb.strategy_name,
                    timeframe=cb.timeframe,
                    signal=cb.signal,
                    confidence=cb.confidence,
                    strength=cb.strength,
                    score=cb.score,
                    weight=cb.weight,
                    entry_contribution=cb.entry_contribution,
                    sl_contribution=cb.sl_contribution,
                    tp_contribution=cb.tp_contribution,
                    reason=cb.reason
                ) for cb in recommendation.contribution_breakdown
            ]

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
            contribution_breakdown=contribution_breakdown,
            risk_reward_ratio=recommendation.risk_reward_ratio,
            entry_label=recommendation.entry_label,
            risk_percentage=recommendation.risk_percentage,
            normalized_weights_sum=recommendation.normalized_weights_sum,
            position_size_usd=recommendation.position_size_usd,
            position_size_pct=recommendation.position_size_pct
        )
        
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

# WebSocket route
from backend.api.routes.websocket import manager, websocket_endpoint
app.add_websocket_route("/ws", websocket_endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
