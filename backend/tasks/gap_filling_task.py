"""Task for detecting and filling gaps in historical data."""
import logging
from typing import List, Dict
from datetime import datetime, timedelta

from backend.repositories.ohlcv_repository import OHLCVRepository
from backend.repositories.ingestion_repository import IngestionRepository
from data.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class GapFillingTask:
    """Detect and fill gaps in OHLCV data."""
    
    def __init__(self):
        """Initialize gap filling task."""
        self.ohlcv_repo = OHLCVRepository()
        self.ingestion_repo = IngestionRepository()
        self.binance_client = BinanceClient()
    
    def _get_interval_minutes(self, timeframe: str) -> int:
        """Get interval in minutes for a timeframe."""
        interval_map = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
        }
        return interval_map.get(timeframe, 60)
    
    def detect_gaps(self, symbol: str, timeframe: str, 
                    start_timestamp: int = None, end_timestamp: int = None) -> List[Dict]:
        """Detect gaps in data for a symbol/timeframe."""
        # Get latest candle
        latest = self.ohlcv_repo.get_latest(symbol, timeframe)
        
        if not latest:
            return []
        
        # Determine range
        if not end_timestamp:
            end_timestamp = latest['timestamp']
        
        if not start_timestamp:
            # Look back 7 days by default
            interval_ms = self._get_interval_minutes(timeframe) * 60 * 1000
            days_back = 7
            start_timestamp = end_timestamp - (days_back * 24 * 60 * 60 * 1000)
        
        # Get all candles in range
        candles = self.ohlcv_repo.get_range(symbol, timeframe, start_timestamp, end_timestamp)
        
        if not candles:
            return []
        
        # Sort by timestamp
        candles.sort(key=lambda x: x['timestamp'])
        
        # Detect gaps
        gaps = []
        interval_ms = self._get_interval_minutes(timeframe) * 60 * 1000
        expected_interval = interval_ms * 1.5  # 50% tolerance
        
        for i in range(1, len(candles)):
            current_ts = candles[i]['timestamp']
            previous_ts = candles[i-1]['timestamp']
            actual_interval = current_ts - previous_ts
            
            if actual_interval > expected_interval:
                gap_start = previous_ts + interval_ms
                gap_end = current_ts - interval_ms
                
                expected_candles = int((gap_end - gap_start) / interval_ms)
                
                gaps.append({
                    'start_timestamp': gap_start,
                    'end_timestamp': gap_end,
                    'expected_candles': expected_candles,
                    'actual_interval_ms': actual_interval
                })
        
        return gaps
    
    def fill_gap(self, symbol: str, timeframe: str, gap: Dict) -> int:
        """Fill a single gap by fetching missing data."""
        try:
            logger.info(f"Filling gap for {symbol} {timeframe}: {gap['start_timestamp']} to {gap['end_timestamp']}")
            
            # Fetch candles for gap period
            candles = self.binance_client.get_historical_candles(
                symbol=symbol,
                interval=timeframe,
                start_time=gap['start_timestamp'],
                end_time=gap['end_timestamp'],
                limit=1000
            )
            
            if not candles:
                return 0
            
            # Add symbol and timeframe to each candle
            for candle in candles:
                candle['symbol'] = symbol
                candle['timeframe'] = timeframe
            
            # Save to database
            saved = self.ohlcv_repo.save_batch(candles)
            
            logger.info(f"Filled gap: {saved} candles saved")
            return saved
            
        except Exception as e:
            logger.error(f"Error filling gap: {e}")
            return 0
    
    def run(self, symbols: List[str], timeframes: List[str]) -> Dict:
        """Run gap detection and filling for all symbol/timeframe combinations."""
        results = {}
        
        for symbol in symbols:
            for timeframe in timeframes:
                try:
                    gaps = self.detect_gaps(symbol, timeframe)
                    
                    if gaps:
                        logger.info(f"Found {len(gaps)} gaps for {symbol} {timeframe}")
                        filled_count = 0
                        
                        for gap in gaps:
                            filled = self.fill_gap(symbol, timeframe, gap)
                            filled_count += filled
                        
                        results[f"{symbol}_{timeframe}"] = {
                            'gaps_found': len(gaps),
                            'candles_filled': filled_count
                        }
                    else:
                        results[f"{symbol}_{timeframe}"] = {
                            'gaps_found': 0,
                            'candles_filled': 0
                        }
                        
                except Exception as e:
                    logger.error(f"Error processing {symbol} {timeframe}: {e}")
                    results[f"{symbol}_{timeframe}"] = {
                        'error': str(e)
                    }
        
        return results


if __name__ == '__main__':
    import os
    
    symbols = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')
    timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')
    
    task = GapFillingTask()
    results = task.run(symbols, timeframes)
    
    print("Gap filling results:")
    for key, result in results.items():
        print(f"  {key}: {result}")

