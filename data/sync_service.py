"""Service for syncing OHLCV data from Binance and persisting to CSV files."""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from pathlib import Path

from data.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class SyncService:
    """Service for managing OHLCV data sync with Binance."""
    
    def __init__(self, binance_client: BinanceClient, data_dir: str = "data/ohlcv"):
        """Initialize sync service."""
        self.binance_client = binance_client
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"SyncService initialized with data_dir: {data_dir}")
    
    def download_historical_data(self, symbol: str, timeframes: List[str], 
                                days_back: int = 365) -> Dict[str, str]:
        """Download historical data for multiple timeframes."""
        results = {}
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        for timeframe in timeframes:
            try:
                logger.info(f"Downloading {symbol} {timeframe} data...")
                candles = self.binance_client.get_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=int(start_time.timestamp() * 1000),
                    limit=1000
                )
                
                if candles:
                    filepath = self._save_to_csv(candles, symbol, timeframe)
                    results[timeframe] = filepath
                    logger.info(f"Saved {len(candles)} candles to {filepath}")
                else:
                    logger.warning(f"No data returned for {timeframe}")
                    results[timeframe] = None
            except Exception as e:
                logger.error(f"Error downloading {timeframe} data: {e}")
                results[timeframe] = None
        
        return results
    
    def refresh_latest_candles(self, symbol: str, timeframes: List[str]) -> Dict[str, bool]:
        """Refresh latest candles for each timeframe from last recorded timestamp."""
        results = {}
        
        for timeframe in timeframes:
            try:
                filepath = self._get_filepath(symbol, timeframe)
                
                if not os.path.exists(filepath):
                    logger.warning(f"File not found: {filepath}, skipping refresh")
                    results[timeframe] = False
                    continue
                
                # Read existing data
                df = pd.read_csv(filepath)
                
                if df.empty:
                    logger.warning(f"Empty CSV for {timeframe}, running full download")
                    results[timeframe] = self._full_download_fallback(symbol, timeframe)
                    continue
                
                # Get last timestamp
                last_timestamp = int(df['timestamp'].iloc[-1])
                
                # Fetch new candles from Binance
                new_candles = self.binance_client.get_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=last_timestamp,
                    limit=1000
                )
                
                if new_candles:
                    # Filter out duplicates
                    new_df = pd.DataFrame(new_candles)
                    new_df = new_df[new_df['timestamp'] > last_timestamp]
                    
                    if not new_df.empty:
                        # Append to existing data
                        df = pd.concat([df, new_df], ignore_index=True)
                        self._save_dataframe(df, filepath)
                        logger.info(f"Updated {timeframe}: added {len(new_df)} new candles")
                        results[timeframe] = True
                    else:
                        logger.info(f"No new candles for {timeframe}")
                        results[timeframe] = True
                else:
                    logger.warning(f"No data returned from Binance for {timeframe}")
                    results[timeframe] = False
                    
            except Exception as e:
                logger.error(f"Error refreshing {timeframe}: {e}")
                results[timeframe] = False
        
        return results
    
    def validate_current_day_data(self, symbol: str, timeframe: str) -> Dict[str, any]:
        """Validate and correct current day data."""
        filepath = self._get_filepath(symbol, timeframe)
        
        if not os.path.exists(filepath):
            return {"valid": False, "message": "File not found"}
        
        try:
            df = pd.read_csv(filepath)
            
            if df.empty:
                return {"valid": False, "message": "Empty file"}
            
            # Get server time
            server_time = self.binance_client.get_server_time()
            server_date = datetime.fromtimestamp(server_time / 1000).date()
            
            # Get latest candle timestamp
            latest_timestamp = df['timestamp'].iloc[-1]
            latest_date = datetime.fromtimestamp(latest_timestamp / 1000).date()
            
            validation_result = {
                "valid": True,
                "server_date": server_date.isoformat(),
                "latest_candle_date": latest_date.isoformat(),
                "is_stale": latest_date < server_date,
                "missing_current": latest_date < server_date
            }
            
            # If missing current day, fetch it
            if validation_result["missing_current"]:
                logger.info(f"Fetching current day data for {timeframe}")
                current_candles = self.binance_client.get_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=int(server_date.timestamp() * 1000)
                )
                
                if current_candles:
                    new_df = pd.DataFrame(current_candles)
                    df = pd.concat([df, new_df], ignore_index=True)
                    self._save_dataframe(df, filepath)
                    validation_result["updated"] = True
                    logger.info(f"Updated with current day data")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {"valid": False, "message": str(e)}
    
    def load_ohlcv_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load OHLCV data from CSV."""
        filepath = self._get_filepath(symbol, timeframe)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        df = pd.read_csv(filepath)
        return df
    
    def _save_to_csv(self, candles: List[Dict], symbol: str, timeframe: str) -> str:
        """Save candles to CSV file."""
        df = pd.DataFrame(candles)
        filepath = self._get_filepath(symbol, timeframe)
        self._save_dataframe(df, filepath)
        return str(filepath)
    
    def _save_dataframe(self, df: pd.DataFrame, filepath: str):
        """Save dataframe to CSV."""
        df.to_csv(filepath, index=False)
    
    def _get_filepath(self, symbol: str, timeframe: str) -> str:
        """Get filepath for symbol and timeframe."""
        filename = f"{symbol}_{timeframe}.csv"
        return str(self.data_dir / filename)
    
    def _full_download_fallback(self, symbol: str, timeframe: str) -> bool:
        """Fallback to full download if file doesn't exist."""
        try:
            candles = self.binance_client.get_historical_candles(
                symbol=symbol,
                interval=timeframe,
                limit=1000
            )
            
            if candles:
                filepath = self._save_to_csv(candles, symbol, timeframe)
                logger.info(f"Full download completed for {timeframe}")
                return True
            return False
        except Exception as e:
            logger.error(f"Full download failed: {e}")
            return False

