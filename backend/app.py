"""FastAPI application for Black Trade backend."""
import os
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd

from data.binance_client import BinanceClient
from data.sync_service import SyncService
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.ichimoku_strategy import IchimokuStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.momentum_strategy import MomentumStrategy
from backtest.engine import BacktestEngine
from recommendation.aggregator import RecommendationAggregator

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Black Trade API", version="1.0.0")

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
recommendation_agg = RecommendationAggregator()

# Cache for results
last_results = {}

class RefreshResponse(BaseModel):
    success: bool
    message: str
    results: Dict[str, Any]

class RecommendationResponse(BaseModel):
    action: str
    confidence: float
    entry_range: Dict[str, float]
    stop_loss: float
    take_profit: float
    current_price: float

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
        timeframes = os.getenv('TIMEFRAMES', '1h,4h,1d,1w').split(',')
        
        # Refresh data
        logger.info("Refreshing data...")
        refresh_results = sync_service.refresh_latest_candles(symbol, timeframes)
        
        # If no data files exist, download initial data
        if not any(refresh_results.values()):
            logger.info("No data files found. Downloading initial historical data...")
            download_results = sync_service.download_historical_data(symbol, timeframes, days_back=365)
            logger.info(f"Downloaded initial data: {download_results}")
        
        # Run backtests for each timeframe
        strategies = [
            EMARSIStrategy(),
            IchimokuStrategy(),
            BreakoutStrategy(),
            MeanReversionStrategy(),
            MomentumStrategy()
        ]
        all_results = {}
        
        for timeframe in timeframes:
            try:
                data = sync_service.load_ohlcv_data(symbol, timeframe)
                if data.empty:
                    continue
                
                results = backtest_engine.run_multiple_backtests(strategies, data, timeframe)
                ranked_results = backtest_engine.rank_strategies(results)
                all_results[timeframe] = ranked_results
            except Exception as e:
                logger.error(f"Error processing {timeframe}: {e}")
                continue
        
        last_results = all_results
        
        return RefreshResponse(
            success=True,
            message="Data refreshed and backtests completed",
            results=all_results
        )
        
    except Exception as e:
        logger.error(f"Error in refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendation")
async def get_recommendation() -> RecommendationResponse:
    """Get current trading recommendation."""
    if not last_results:
        raise HTTPException(status_code=404, detail="No results available. Please call /refresh first.")
    
    try:
        current_price = binance_client.get_current_price('BTCUSDT') if binance_client else 0
        
        # Get top strategies
        top_strategies = []
        signals = []
        
        for timeframe, results in last_results.items():
            if results:
                top_strategy = results[0]
                top_strategies.append(top_strategy)
                signals.append({
                    "strategy_name": top_strategy['strategy_name'],
                    "signal": 1 if top_strategy.get('net_pnl', 0) > 0 else -1,
                    "current_price": current_price
                })
        
        recommendation = recommendation_agg.generate_recommendation(top_strategies, signals)
        
        return RecommendationResponse(**recommendation)
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
