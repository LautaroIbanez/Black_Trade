"""Service for syncing OHLCV data from Binance and persisting to CSV files."""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path
import time

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
        """Download historical data for multiple timeframes with pagination support."""
        results = {}
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        for timeframe in timeframes:
            try:
                logger.info(f"Downloading {symbol} {timeframe} data...")
                all_candles = self._download_with_pagination(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=int(start_time.timestamp() * 1000),
                    end_time=int(end_time.timestamp() * 1000)
                )
                
                if all_candles:
                    filepath = self._save_to_csv(all_candles, symbol, timeframe)
                    results[timeframe] = filepath
                    logger.info(f"Saved {len(all_candles)} candles to {filepath}")
                else:
                    logger.warning(f"No data returned for {timeframe}")
                    results[timeframe] = None
            except Exception as e:
                logger.error(f"Error downloading {timeframe} data: {e}")
                results[timeframe] = None
        
        return results
    
    def _download_with_pagination(self, symbol: str, interval: str, 
                                 start_time: int, end_time: int, 
                                 limit: int = 1000) -> List[Dict]:
        """Download data with pagination to handle large date ranges."""
        all_candles = []
        current_start = start_time
        max_requests = 100  # Safety limit
        request_count = 0
        
        while current_start < end_time and request_count < max_requests:
            try:
                logger.info(f"Fetching batch {request_count + 1} for {symbol} {interval}")
                candles = self.binance_client.get_historical_candles(
                    symbol=symbol,
                    interval=interval,
                    start_time=current_start,
                    limit=limit
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Update start time to last candle timestamp + 1
                last_timestamp = candles[-1]['timestamp']
                current_start = last_timestamp + 1
                request_count += 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in pagination batch {request_count + 1}: {e}")
                break
        
        # Remove duplicates and sort by timestamp
        if all_candles:
            df = pd.DataFrame(all_candles)
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
            all_candles = df.to_dict('records')
        
        return all_candles
    
    def refresh_latest_candles(self, symbol: str, timeframes: List[str]) -> Dict[str, bool]:
        """Refresh latest candles for each timeframe from last recorded timestamp with pagination and overlap buffer."""
        results = {}
        
        for timeframe in timeframes:
            try:
                filepath = self._get_filepath(symbol, timeframe)
                
                if not os.path.exists(filepath):
                    logger.warning(f"File not found: {filepath}, performing initial download for {timeframe}")
                    ok = self._full_download_fallback(symbol, timeframe)
                    results[timeframe] = ok
                    # Continue to next timeframe after initial fetch
                    continue
                
                # Read existing data
                df = pd.read_csv(filepath)
                
                if df.empty:
                    logger.warning(f"Empty CSV for {timeframe}, running full download")
                    results[timeframe] = self._full_download_fallback(symbol, timeframe)
                    continue
                
                # Get last timestamp and compute an overlap buffer of one interval
                last_timestamp = int(df['timestamp'].iloc[-1])
                interval_ms = self._get_interval_minutes(timeframe) * 60 * 1000
                overlap_ms = interval_ms  # re-fetch last full interval to ensure continuity

                # Paginate until no more data
                aggregated_new: List[Dict] = []
                current_start = max(0, last_timestamp + 1 - overlap_ms)
                max_requests = 50
                req = 0
                while req < max_requests:
                    batch = self.binance_client.get_historical_candles(
                        symbol=symbol,
                        interval=timeframe,
                        start_time=current_start,
                        limit=1000
                    )
                    if not batch:
                        break
                    aggregated_new.extend(batch)
                    current_start = int(batch[-1]['timestamp']) + 1
                    req += 1
                    time.sleep(0.1)

                if aggregated_new:
                    new_df = pd.DataFrame(aggregated_new)
                    # Drop duplicates and keep only strictly newer than last stored (post-overlap)
                    merged = pd.concat([df, new_df], ignore_index=True)
                    merged = merged.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
                    added = len(merged) - len(df)
                    if added > 0:
                        self._save_dataframe(merged, filepath)
                        logger.info(f"Updated {timeframe}: added {added} new candles")
                    else:
                        logger.info(f"No new candles for {timeframe}")
                    results[timeframe] = True
                else:
                    logger.info(f"No new candles for {timeframe}")
                    results[timeframe] = True
                    
            except Exception as e:
                logger.error(f"Error refreshing {timeframe}: {e}")
                results[timeframe] = False
        
        return results
    
    def detect_and_fill_gaps(self, symbol: str, timeframes: List[str]) -> Dict[str, Dict]:
        """Detect and fill gaps in historical data."""
        results = {}
        
        for timeframe in timeframes:
            try:
                filepath = self._get_filepath(symbol, timeframe)
                
                if not os.path.exists(filepath):
                    logger.warning(f"File not found: {filepath}")
                    results[timeframe] = {"gaps_found": 0, "gaps_filled": 0, "error": "File not found"}
                    continue
                
                df = pd.read_csv(filepath)
                if df.empty:
                    results[timeframe] = {"gaps_found": 0, "gaps_filled": 0, "error": "Empty file"}
                    continue
                
                # Detect gaps
                gaps = self._detect_gaps(df, timeframe)
                
                if gaps:
                    logger.info(f"Found {len(gaps)} gaps in {timeframe} data")
                    filled_gaps = self._fill_gaps(symbol, timeframe, gaps, df)
                    
                    if filled_gaps:
                        # Save updated data
                        updated_df = self._merge_gap_data(df, filled_gaps)
                        self._save_dataframe(updated_df, filepath)
                        logger.info(f"Filled {len(filled_gaps)} gaps in {timeframe}")
                    
                    results[timeframe] = {
                        "gaps_found": len(gaps),
                        "gaps_filled": len(filled_gaps) if filled_gaps else 0,
                        "gaps": gaps
                    }
                else:
                    results[timeframe] = {"gaps_found": 0, "gaps_filled": 0}
                    
            except Exception as e:
                logger.error(f"Error detecting gaps for {timeframe}: {e}")
                results[timeframe] = {"gaps_found": 0, "gaps_filled": 0, "error": str(e)}
        
        return results
    
    def _detect_gaps(self, df: pd.DataFrame, timeframe: str) -> List[Dict]:
        """Detect gaps in the data based on expected interval."""
        if df.empty:
            return []
        
        # Convert timestamp to datetime
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.sort_values('datetime')
        
        # Calculate expected interval in minutes
        interval_minutes = self._get_interval_minutes(timeframe)
        expected_interval = pd.Timedelta(minutes=interval_minutes)
        
        gaps = []
        for i in range(1, len(df)):
            current_time = df.iloc[i]['datetime']
            previous_time = df.iloc[i-1]['datetime']
            actual_interval = current_time - previous_time
            
            # Check if there's a gap larger than expected
            if actual_interval > expected_interval * 1.5:  # 50% tolerance
                gap_start = previous_time + expected_interval
                gap_end = current_time - expected_interval
                
                gaps.append({
                    "start_time": gap_start,
                    "end_time": gap_end,
                    "expected_candles": int((gap_end - gap_start) / expected_interval),
                    "actual_interval": actual_interval.total_seconds() / 60
                })
        
        return gaps
    
    def _get_interval_minutes(self, timeframe: str) -> int:
        """Get interval in minutes for a timeframe."""
        interval_map = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
        }
        return interval_map.get(timeframe, 60)
    
    def _fill_gaps(self, symbol: str, timeframe: str, gaps: List[Dict], 
                   existing_df: pd.DataFrame) -> List[Dict]:
        """Fill detected gaps by fetching missing data."""
        filled_data = []
        
        for gap in gaps:
            try:
                start_timestamp = int(gap['start_time'].timestamp() * 1000)
                end_timestamp = int(gap['end_time'].timestamp() * 1000)
                
                logger.info(f"Filling gap from {gap['start_time']} to {gap['end_time']}")
                
                # Fetch data for the gap period
                gap_candles = self.binance_client.get_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    limit=1000
                )
                
                if gap_candles:
                    filled_data.extend(gap_candles)
                    logger.info(f"Filled gap with {len(gap_candles)} candles")
                
                # Rate limiting
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error filling gap: {e}")
                continue
        
        return filled_data
    
    def _merge_gap_data(self, existing_df: pd.DataFrame, gap_data: List[Dict]) -> pd.DataFrame:
        """Merge gap data with existing data."""
        if not gap_data:
            return existing_df
        
        gap_df = pd.DataFrame(gap_data)
        
        # Combine and deduplicate
        combined_df = pd.concat([existing_df, gap_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        return combined_df
    
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
                server_datetime = datetime.combine(server_date, datetime.min.time())
                current_candles = self.binance_client.get_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=int(server_datetime.timestamp() * 1000)
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

