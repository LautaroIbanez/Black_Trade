"""
Chart data API routes.

Provides candle data with trading signals and levels for visualization.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from data.sync_service import SyncService
from data.binance_client import BinanceClient
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service

router = APIRouter()

# Initialize services
binance_client = BinanceClient()
sync_service = SyncService(binance_client)


class CandleData(BaseModel):
    """Single candle data point."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    datetime: str


class SignalLevel(BaseModel):
    """Trading signal level."""
    price: float
    level_type: str  # 'entry', 'stop_loss', 'take_profit'
    strategy: str
    confidence: float
    reason: str


class ChartData(BaseModel):
    """Complete chart data with signals."""
    symbol: str
    timeframe: str
    candles: List[CandleData]
    signals: List[SignalLevel]
    current_price: float
    recommendation: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]


@router.get("/chart/{symbol}/{timeframe}", response_model=ChartData)
async def get_chart_data(
    symbol: str,
    timeframe: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of candles to return"),
    include_signals: bool = Query(True, description="Include trading signals"),
    include_recommendation: bool = Query(True, description="Include current recommendation")
) -> ChartData:
    """
    Get chart data with trading signals and levels.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Timeframe (e.g., '1h', '4h', '1d')
        limit: Number of candles to return (1-1000)
        include_signals: Whether to include trading signals
        include_recommendation: Whether to include current recommendation
    
    Returns:
        ChartData with candles, signals, and recommendation
    """
    try:
        # Validate timeframe
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        if timeframe not in valid_timeframes:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid timeframe. Must be one of: {valid_timeframes}"
            )
        
        # Load OHLCV data
        try:
            df = sync_service.load_ohlcv_data(symbol, timeframe)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for {symbol} {timeframe}. Please call /refresh first."
            )
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Empty dataset for {symbol} {timeframe}"
            )
        
        # Get latest N candles
        df = df.tail(limit).copy()
        
        # Convert to chart format
        candles = []
        for _, row in df.iterrows():
            candles.append(CandleData(
                timestamp=int(row['timestamp']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=float(row['volume']),
                datetime=datetime.fromtimestamp(row['timestamp'] / 1000).isoformat()
            ))
        
        # Get current price
        current_price = float(df['close'].iloc[-1])
        
        # Generate signals if requested
        signals = []
        if include_signals:
            signals = await _generate_chart_signals(df, symbol, timeframe)
        
        # Get current recommendation if requested
        recommendation = None
        if include_recommendation:
            try:
                # Load current data for all timeframes
                timeframes = os.getenv('TIMEFRAMES', '1h,4h,1d,1w').split(',')
                current_data = {}
                for tf in timeframes:
                    try:
                        tf_data = sync_service.load_ohlcv_data(symbol, tf)
                        if not tf_data.empty:
                            current_data[tf] = tf_data
                    except Exception:
                        continue
                
                if current_data:
                    # Get last results from global state (simplified for this example)
                    # In a real implementation, you'd get this from a proper state management
                    recommendation = await _get_current_recommendation(current_data)
            except Exception as e:
                # Recommendation is optional, don't fail the entire request
                recommendation = None

        # Ensure recommendation shape is consistent for frontend rendering
        if include_recommendation and recommendation is None:
            recommendation = {
                "action": "HOLD",
                "confidence": 0.0,
                "entry_range": {"min": current_price, "max": current_price},
                "stop_loss": current_price,
                "take_profit": current_price,
                "current_price": current_price,
                "primary_strategy": "None",
                "risk_level": "LOW"
            }
        
        # Prepare metadata
        metadata = {
            "total_candles": len(candles),
            "date_range": {
                "start": candles[0].datetime if candles else None,
                "end": candles[-1].datetime if candles else None
            },
            "timeframe_minutes": _get_timeframe_minutes(timeframe),
            "data_freshness_hours": _calculate_freshness(df),
            "signals_count": len(signals)
        }
        
        return ChartData(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            signals=signals,
            current_price=current_price,
            recommendation=recommendation,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")


async def _generate_chart_signals(df: pd.DataFrame, symbol: str, timeframe: str) -> List[SignalLevel]:
    """Generate trading signals for chart display."""
    signals = []
    
    try:
        # Get enabled strategies
        strategies = strategy_registry.get_enabled_strategies()
        
        # Generate signals for each strategy
        for strategy in strategies:
            try:
                signal_data = strategy.generate_signal(df)
                entry_range = strategy.entry_range(df, signal_data['signal'])
                risk_targets = strategy.risk_targets(df, signal_data['signal'], signal_data['price'])
                
                # Add entry range
                if signal_data['signal'] != 0:
                    signals.append(SignalLevel(
                        price=entry_range['min'],
                        level_type='entry',
                        strategy=strategy.name,
                        confidence=signal_data['confidence'],
                        reason=f"{strategy.name}: {signal_data['reason']}"
                    ))
                    
                    signals.append(SignalLevel(
                        price=entry_range['max'],
                        level_type='entry',
                        strategy=strategy.name,
                        confidence=signal_data['confidence'],
                        reason=f"{strategy.name}: {signal_data['reason']}"
                    ))
                
                # Add stop loss and take profit
                if signal_data['signal'] != 0:
                    signals.append(SignalLevel(
                        price=risk_targets['stop_loss'],
                        level_type='stop_loss',
                        strategy=strategy.name,
                        confidence=signal_data['confidence'],
                        reason=f"{strategy.name} SL"
                    ))
                    
                    signals.append(SignalLevel(
                        price=risk_targets['take_profit'],
                        level_type='take_profit',
                        strategy=strategy.name,
                        confidence=signal_data['confidence'],
                        reason=f"{strategy.name} TP"
                    ))
                    
            except Exception as e:
                # Skip strategies that fail
                continue
                
    except Exception as e:
        # Return empty signals if generation fails
        pass
    
    return signals


async def _get_current_recommendation(current_data: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """Get current trading recommendation."""
    try:
        # Import the global last_results from the main app
        from backend.app import last_results
        
        # Use the same recommendation generation as the main endpoint
        recommendation = recommendation_service.generate_recommendation(current_data, last_results)
        
        return {
            "action": recommendation.action,
            "confidence": recommendation.confidence,
            "entry_range": recommendation.entry_range,
            "stop_loss": recommendation.stop_loss,
            "take_profit": recommendation.take_profit,
            "current_price": recommendation.current_price,
            "primary_strategy": recommendation.primary_strategy,
            "supporting_strategies": recommendation.supporting_strategies,
            "strategy_details": recommendation.strategy_details,
            "signal_consensus": recommendation.signal_consensus,
            "risk_level": recommendation.risk_level
        }
    except Exception:
        return None


def _get_timeframe_minutes(timeframe: str) -> int:
    """Get timeframe in minutes."""
    timeframe_map = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
        '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
    }
    return timeframe_map.get(timeframe, 60)


def _calculate_freshness(df: pd.DataFrame) -> float:
    """Calculate data freshness in hours."""
    if df.empty:
        return float('inf')
    
    latest_timestamp = df['timestamp'].iloc[-1]
    latest_datetime = datetime.fromtimestamp(latest_timestamp / 1000)
    current_time = datetime.now()
    
    return (current_time - latest_datetime).total_seconds() / 3600


@router.get("/chart/symbols")
async def get_available_symbols() -> Dict[str, List[str]]:
    """Get available trading symbols and timeframes."""
    return {
        "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"],
        "timeframes": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]
    }


@router.get("/chart/status")
async def get_chart_status() -> Dict[str, Any]:
    """Get chart service status and data availability."""
    try:
        symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        timeframes = os.getenv('TIMEFRAMES', '1h,4h,1d,1w').split(',')
        
        status = {
            "service_status": "active",
            "available_data": {},
            "last_updated": None
        }
        
        for timeframe in timeframes:
            try:
                df = sync_service.load_ohlcv_data(symbol, timeframe)
                if not df.empty:
                    latest_timestamp = df['timestamp'].iloc[-1]
                    latest_datetime = datetime.fromtimestamp(latest_timestamp / 1000)
                    
                    status["available_data"][timeframe] = {
                        "candles": len(df),
                        "last_update": latest_datetime.isoformat(),
                        "freshness_hours": _calculate_freshness(df)
                    }
                    
                    if status["last_updated"] is None or latest_datetime > datetime.fromisoformat(status["last_updated"]):
                        status["last_updated"] = latest_datetime.isoformat()
            except Exception:
                status["available_data"][timeframe] = {
                    "candles": 0,
                    "error": "No data available"
                }
        
        return status
        
    except Exception as e:
        return {
            "service_status": "error",
            "error": str(e)
        }
