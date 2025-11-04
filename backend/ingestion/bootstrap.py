"""Bootstrap module for populating initial historical market data."""
import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    # Dummy tqdm for compatibility
    class tqdm:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def update(self, n=1):
            pass

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from data.binance_client import BinanceClient
from backend.repositories.ohlcv_repository import OHLCVRepository
from backend.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class DataBootstrap:
    """Bootstrap historical market data from exchange."""
    
    def __init__(self, binance_client: Optional[BinanceClient] = None):
        """Initialize bootstrap service."""
        self.binance_client = binance_client or BinanceClient()
        self.repo = OHLCVRepository()
        self.market_data_service = MarketDataService()
        
    def get_required_days(self, timeframe: str) -> int:
        """Get number of days of history required for a timeframe."""
        # Minimum required days for backtesting/analysis
        requirements = {
            '1m': 7,      # 7 days for 1m
            '5m': 14,     # 2 weeks for 5m
            '15m': 30,    # 1 month for 15m
            '1h': 90,     # 3 months for 1h
            '4h': 180,    # 6 months for 4h
            '1d': 365,    # 1 year for daily
            '1w': 730,    # 2 years for weekly
        }
        return requirements.get(timeframe, 90)  # Default 90 days
    
    def get_candles_per_request(self, timeframe: str) -> int:
        """Get optimal number of candles per API request."""
        # Binance limit is 1000, but we use smaller chunks to be safe
        return 500
    
    def calculate_total_candles(self, timeframe: str, days: int) -> int:
        """Calculate total candles needed for timeframe and days."""
        timeframe_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '1w': 10080,
        }
        minutes_per_candle = timeframe_minutes.get(timeframe, 60)
        total_minutes = days * 24 * 60
        return total_minutes // minutes_per_candle
    
    async def populate_historical(
        self,
        symbol: str,
        timeframe: str,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Populate historical data for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h', '4h', '1d')
            days: Number of days to fetch (if not using start_date/end_date)
            start_date: Start date (optional)
            end_date: End date (optional, defaults to now)
            progress_callback: Optional callback(processed, total, symbol, timeframe)
            
        Returns:
            Dictionary with results: {symbol, timeframe, candles_fetched, candles_saved, errors}
        """
        results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'candles_fetched': 0,
            'candles_saved': 0,
            'errors': [],
            'start_timestamp': None,
            'end_timestamp': None,
        }
        
        try:
            # Determine date range
            if end_date is None:
                end_date = datetime.now()
            
            if start_date is None:
                if days is None:
                    days = self.get_required_days(timeframe)
                start_date = end_date - timedelta(days=days)
            
            results['start_timestamp'] = int(start_date.timestamp() * 1000)
            results['end_timestamp'] = int(end_date.timestamp() * 1000)
            
            logger.info(f"Populating {symbol} {timeframe} from {start_date} to {end_date}")
            
            # Calculate total candles needed
            total_candles = self.calculate_total_candles(timeframe, (end_date - start_date).days)
            candles_per_request = self.get_candles_per_request(timeframe)
            
            # Fetch in chunks - iterate properly from start_date to end_date
            current_start_ts = int(start_date.timestamp() * 1000)
            end_ts_ms = int(end_date.timestamp() * 1000)
            all_candles = []
            request_count = 0
            seen_timestamps = set()  # Global deduplication
            
            with tqdm(total=total_candles, desc=f"{symbol} {timeframe}", unit="candle") as pbar:
                while current_start_ts < end_ts_ms:
                    try:
                        # Fetch candles - Binance returns up to limit candles starting from startTime
                        candles = self.binance_client.get_historical_candles(
                            symbol=symbol,
                            interval=timeframe,
                            start_time=current_start_ts,
                            end_time=end_ts_ms,
                            limit=candles_per_request
                        )
                        
                        if not candles:
                            # No more data available
                            logger.debug(f"No more candles for {symbol} {timeframe} after {datetime.fromtimestamp(current_start_ts / 1000)}")
                            break
                        
                        # Filter out duplicates and candles beyond end_date
                        formatted_candles = []
                        for candle in candles:
                            candle_ts = candle['timestamp']
                            
                            # Skip if beyond end date
                            if candle_ts > end_ts_ms:
                                continue
                            
                            # Skip duplicates
                            if candle_ts in seen_timestamps:
                                continue
                            
                            seen_timestamps.add(candle_ts)
                            
                            formatted_candles.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'timestamp': candle_ts,
                                'open': candle['open'],
                                'high': candle['high'],
                                'low': candle['low'],
                                'close': candle['close'],
                                'volume': candle['volume'],
                                'quote_volume': candle.get('quote_volume'),
                                'trades': candle.get('trades'),
                                'taker_buy_base': candle.get('taker_buy_base'),
                                'taker_buy_quote': candle.get('taker_buy_quote'),
                                'close_time': candle.get('close_time'),
                            })
                        
                        if not formatted_candles:
                            # All duplicates or beyond end date, we're done
                            logger.debug(f"No new candles in response for {symbol} {timeframe}")
                            break
                        
                        all_candles.extend(formatted_candles)
                        results['candles_fetched'] += len(formatted_candles)
                        
                        # Update progress
                        pbar.update(len(formatted_candles))
                        if progress_callback:
                            progress_callback(results['candles_fetched'], total_candles, symbol, timeframe)
                        
                        # Move to next chunk: start from the last candle timestamp + 1ms
                        # This ensures we don't miss any candles and don't get duplicates
                        last_timestamp = formatted_candles[-1]['timestamp']
                        current_start_ts = last_timestamp + 1  # Next millisecond
                        
                        # If we got fewer candles than requested, we're likely at the end
                        if len(candles) < candles_per_request:
                            # Verify we've reached or passed end date
                            if last_timestamp >= end_ts_ms:
                                break
                        
                        request_count += 1
                        
                        # Rate limiting: Binance allows 1200 requests/minute
                        # Wait 50ms between requests to be safe
                        await asyncio.sleep(0.05)
                        
                    except Exception as e:
                        error_msg = f"Error fetching chunk starting at {datetime.fromtimestamp(current_start_ts / 1000)}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        # Move forward by calculating next interval to skip problematic range
                        timeframe_minutes = {
                            '1m': 1, '5m': 5, '15m': 15, '1h': 60,
                            '4h': 240, '1d': 1440, '1w': 10080,
                        }
                        interval_ms = timeframe_minutes.get(timeframe, 60) * 60 * 1000
                        # Skip forward by a reasonable amount (1 hour worth of intervals)
                        current_start_ts += (interval_ms * 60)
                        if current_start_ts >= end_ts_ms:
                            break
            
            # Save all candles in batches
            if all_candles:
                logger.info(f"Saving {len(all_candles)} candles for {symbol} {timeframe}...")
                
                batch_size = 500
                for i in range(0, len(all_candles), batch_size):
                    batch = all_candles[i:i + batch_size]
                    try:
                        saved = self.repo.save_batch(batch)
                        results['candles_saved'] += saved
                    except Exception as e:
                        error_msg = f"Error saving batch {i}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
            
            logger.info(f"✓ Completed {symbol} {timeframe}: {results['candles_saved']} candles saved")
            
        except Exception as e:
            error_msg = f"Fatal error populating {symbol} {timeframe}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    async def populate_all(
        self,
        symbols: List[str],
        timeframes: List[str],
        days: Optional[int] = None
    ) -> Dict:
        """
        Populate historical data for multiple symbols/timeframes.
        
        Args:
            symbols: List of trading symbols
            timeframes: List of timeframes
            days: Number of days to fetch (optional, uses defaults per timeframe)
            
        Returns:
            Summary dictionary with results per symbol/timeframe
        """
        logger.info("=" * 70)
        logger.info("Starting historical data bootstrap")
        logger.info(f"Symbols: {symbols}")
        logger.info(f"Timeframes: {timeframes}")
        logger.info("=" * 70)
        
        summary = {
            'total_symbols': len(symbols),
            'total_timeframes': len(timeframes),
            'results': {},
            'success_count': 0,
            'error_count': 0,
        }
        
        total_tasks = len(symbols) * len(timeframes)
        completed = 0
        
        for symbol in symbols:
            for timeframe in timeframes:
                key = f"{symbol}_{timeframe}"
                try:
                    result = await self.populate_historical(
                        symbol=symbol,
                        timeframe=timeframe,
                        days=days
                    )
                    
                    summary['results'][key] = result
                    
                    if result['errors']:
                        summary['error_count'] += 1
                    else:
                        summary['success_count'] += 1
                    
                    completed += 1
                    logger.info(f"Progress: {completed}/{total_tasks} completed")
                    
                except Exception as e:
                    logger.error(f"Failed to populate {key}: {e}")
                    summary['results'][key] = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'candles_fetched': 0,
                        'candles_saved': 0,
                        'errors': [str(e)],
                    }
                    summary['error_count'] += 1
                    completed += 1
        
        logger.info("=" * 70)
        logger.info("Bootstrap complete")
        logger.info(f"Success: {summary['success_count']}/{total_tasks}")
        logger.info(f"Errors: {summary['error_count']}/{total_tasks}")
        logger.info("=" * 70)
        
        return summary
    
    def verify_data(
        self,
        symbol: str,
        timeframes: List[str]
    ) -> Dict:
        """
        Verify data availability and freshness.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to verify
            
        Returns:
            Verification report
        """
        report = {
            'symbol': symbol,
            'timeframes': {},
            'overall_status': 'ok',
        }
        
        for timeframe in timeframes:
            try:
                count = self.repo.count(symbol, timeframe)
                latest = self.repo.get_latest(symbol, timeframe)
                
                status = 'ok'
                issues = []
                
                if count == 0:
                    status = 'missing'
                    issues.append('No data available')
                elif latest:
                    # Check freshness
                    latest_ts = latest['timestamp']
                    latest_dt = datetime.fromtimestamp(latest_ts / 1000)
                    age_hours = (datetime.now() - latest_dt).total_seconds() / 3600
                    
                    # Expected maximum age per timeframe
                    max_age_hours = {
                        '1m': 0.1, '5m': 0.5, '15m': 1, '1h': 2,
                        '4h': 5, '1d': 25, '1w': 7 * 24,
                    }
                    expected_max_age = max_age_hours.get(timeframe, 24)
                    
                    if age_hours > expected_max_age:
                        status = 'stale'
                        issues.append(f'Data is {age_hours:.1f}h old (expected < {expected_max_age}h)')
                    
                    # Check minimum required candles
                    min_required = self.calculate_total_candles(timeframe, self.get_required_days(timeframe))
                    if count < min_required * 0.8:  # 80% of required
                        status = 'incomplete'
                        issues.append(f'Only {count} candles (expected ~{min_required})')
                
                report['timeframes'][timeframe] = {
                    'status': status,
                    'count': count,
                    'latest_timestamp': latest['timestamp'] if latest else None,
                    'latest_datetime': datetime.fromtimestamp(latest['timestamp'] / 1000).isoformat() if latest else None,
                    'issues': issues,
                }
                
                if status != 'ok':
                    report['overall_status'] = 'incomplete'
                    
            except Exception as e:
                report['timeframes'][timeframe] = {
                    'status': 'error',
                    'error': str(e),
                }
                report['overall_status'] = 'error'
        
        return report


async def main():
    """Main bootstrap entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Bootstrap historical market data')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols (default: from env)')
    parser.add_argument('--timeframes', type=str, help='Comma-separated timeframes (default: from env)')
    parser.add_argument('--days', type=int, help='Number of days to fetch (optional, uses defaults)')
    parser.add_argument('--verify', action='store_true', help='Verify data after bootstrap')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get symbols and timeframes
    symbols = (args.symbols or os.getenv('TRADING_PAIRS', 'BTCUSDT')).split(',')
    timeframes = (args.timeframes or os.getenv('TIMEFRAMES', '15m,1h,4h,1d')).split(',')
    
    # Initialize bootstrap
    bootstrap = DataBootstrap()
    
    # Populate data
    summary = await bootstrap.populate_all(symbols, timeframes, days=args.days)
    
    # Verify if requested
    if args.verify:
        logger.info("\nVerifying data...")
        for symbol in symbols:
            report = bootstrap.verify_data(symbol, timeframes)
            logger.info(f"\nVerification for {symbol}:")
            for tf, data in report['timeframes'].items():
                status = data.get('status', 'unknown')
                count = data.get('count', 0)
                issues = data.get('issues', [])
                logger.info(f"  {tf}: {status} ({count} candles)")
                for issue in issues:
                    logger.info(f"    ⚠ {issue}")
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("Bootstrap Summary")
    logger.info("=" * 70)
    for key, result in summary['results'].items():
        status = "✓" if not result['errors'] else "✗"
        logger.info(f"{status} {key}: {result['candles_saved']} candles saved")
        if result['errors']:
            for error in result['errors']:
                logger.error(f"    Error: {error}")
    
    sys.exit(0 if summary['error_count'] == 0 else 1)


if __name__ == '__main__':
    asyncio.run(main())
