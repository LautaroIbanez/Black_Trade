"""Market data service using SQL repository instead of CSV files."""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

from backend.repositories.ohlcv_repository import OHLCVRepository
from data.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for managing market data using SQL repository."""
    
    def __init__(self, binance_client: Optional[BinanceClient] = None):
        """
        Initialize market data service.
        
        Args:
            binance_client: Optional Binance client for fetching data
        """
        self.repo = OHLCVRepository()
        self.binance_client = binance_client
        logger.info("MarketDataService initialized with SQL repository")
    
    def load_ohlcv_data(
        self,
        symbol: str,
        timeframe: str,
        limit: Optional[int] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Load OHLCV data from database.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h', '4h')
            limit: Maximum number of candles to return
            start_timestamp: Start timestamp (milliseconds)
            end_timestamp: End timestamp (milliseconds)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            df = self.repo.to_dataframe(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
            
            if df.empty:
                logger.warning(f"No data found for {symbol} {timeframe}")
                return pd.DataFrame()
            
            logger.debug(f"Loaded {len(df)} candles for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading OHLCV data: {e}")
            return pd.DataFrame()
    
    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Get the latest candle for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            Latest candle as dictionary or None
        """
        return self.repo.get_latest(symbol, timeframe)
    
    def get_data_summary(self, symbol: str, timeframes: list) -> Dict:
        """
        Get summary of available data.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to check
            
        Returns:
            Summary dictionary
        """
        summary = {
            "symbol": symbol,
            "timeframes": {},
            "overall_status": "ok",
        }
        
        for timeframe in timeframes:
            try:
                count = self.repo.count(symbol, timeframe)
                latest = self.repo.get_latest(symbol, timeframe)
                
                summary["timeframes"][timeframe] = {
                    "candles": count,
                    "latest_timestamp": latest["timestamp"] if latest else None,
                    "latest_datetime": datetime.fromtimestamp(latest["timestamp"] / 1000).isoformat() if latest else None,
                }
                
                if count == 0:
                    summary["overall_status"] = "incomplete"
                    
            except Exception as e:
                logger.error(f"Error getting summary for {timeframe}: {e}")
                summary["timeframes"][timeframe] = {
                    "error": str(e),
                }
                summary["overall_status"] = "error"
        
        return summary
    
    def refresh_latest_candles(self, symbol: str, timeframes: list) -> Dict:
        """
        Refresh latest candles from exchange (if binance_client available).
        
        This method is kept for compatibility but the actual refresh
        should be done by the ingestion pipeline.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes
            
        Returns:
            Results dictionary
        """
        logger.info(f"Refresh latest candles called for {symbol} {timeframes}")
        logger.warning("Refresh should be handled by ingestion pipeline. This is a no-op.")
        
        # Return current status
        results = {}
        for timeframe in timeframes:
            latest = self.get_latest_candle(symbol, timeframe)
            results[timeframe] = latest is not None
        
        return results


