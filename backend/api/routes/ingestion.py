"""API routes for data ingestion status and verification."""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from backend.ingestion.bootstrap import DataBootstrap
from backend.repositories.ingestion_repository import IngestionRepository
from backend.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)
router = APIRouter()

bootstrap = DataBootstrap()
ingestion_repo = IngestionRepository()
market_data_service = MarketDataService()


@router.get("/ingestion/status")
async def get_ingestion_status(
    symbol: str = Query(None, description="Filter by symbol"),
    timeframe: str = Query(None, description="Filter by timeframe")
) -> Dict[str, Any]:
    """
    Get ingestion status for symbols/timeframes.
    
    Returns current ingestion status including:
    - Active ingestion mode (websocket/polling)
    - Last ingested timestamp
    - Status (active/inactive/error)
    """
    try:
        # Get all statuses from repository
        if symbol and timeframe:
            status = ingestion_repo.get_status(symbol, timeframe)
            return {
                "statuses": {f"{symbol}_{timeframe}": status} if status else {},
                "summary": {
                    "total": 1 if status else 0,
                    "active": 1 if status and status.get('status') == 'active' else 0,
                }
            }
        else:
            # Get all statuses (would need to implement in repository)
            # For now, return summary from market data service
            import os
            symbols = (symbol or os.getenv('TRADING_PAIRS', 'BTCUSDT')).split(',')
            timeframes = (timeframe or os.getenv('TIMEFRAMES', '15m,1h,4h,1d')).split(',')
            
            statuses = {}
            active_count = 0
            
            for sym in symbols:
                for tf in timeframes:
                    status = ingestion_repo.get_status(sym, tf)
                    if status:
                        statuses[f"{sym}_{tf}"] = status
                        if status.get('status') == 'active':
                            active_count += 1
            
            return {
                "statuses": statuses,
                "summary": {
                    "total": len(statuses),
                    "active": active_count,
                    "inactive": len(statuses) - active_count,
                }
            }
    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingestion/verify")
async def verify_data(
    symbol: str = Query(None, description="Symbol to verify"),
    timeframes: str = Query(None, description="Comma-separated timeframes to verify")
) -> Dict[str, Any]:
    """
    Verify data availability and freshness.
    
    Checks:
    - Data availability (count)
    - Data freshness (age of latest candle)
    - Completeness (compared to required minimum)
    """
    try:
        import os
        
        if not symbol:
            symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
        
        if not timeframes:
            timeframes_list = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')
        else:
            timeframes_list = [tf.strip() for tf in timeframes.split(',')]
        
        # Run verification
        report = bootstrap.verify_data(symbol, timeframes_list)
        
        return {
            "symbol": symbol,
            "overall_status": report['overall_status'],
            "timeframes": report['timeframes'],
            "verified_at": __import__('datetime').datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error verifying data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ingestion/summary")
async def get_data_summary(
    symbol: str = Query(None, description="Symbol to summarize")
) -> Dict[str, Any]:
    """
    Get summary of available data.
    
    Returns:
    - Count of candles per timeframe
    - Latest timestamp per timeframe
    - Overall status
    """
    try:
        import os
        
        if not symbol:
            symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
        
        timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')
        
        summary = market_data_service.get_data_summary(symbol, timeframes)
        
        return summary
    except Exception as e:
        logger.error(f"Error getting data summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

