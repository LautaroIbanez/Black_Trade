#!/usr/bin/env python
"""Manually populate initial OHLCV data for the database."""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
env_file = project_root / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()

from backend.tasks.data_ingestion_task import DataIngestionTask
from data.binance_client import BinanceClient
from backend.services.market_data_service import MarketDataService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def populate_initial_data():
    """Populate initial OHLCV data using Binance API."""
    logger.info("Starting initial data population...")
    
    symbols = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')
    timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')
    
    logger.info(f"Fetching data for symbols: {symbols}, timeframes: {timeframes}")
    
    # Use BinanceClient to fetch historical data
    try:
        client = BinanceClient()
        market_data_service = MarketDataService()
        
        # Fetch and store data for each symbol/timeframe combination
        for symbol in symbols:
            for timeframe in timeframes:
                logger.info(f"Fetching {symbol} {timeframe}...")
                try:
                    # Fetch last 500 candles (enough for initial backtests)
                    candles = client.get_historical_candles(symbol, timeframe, limit=500)
                    if candles and len(candles) > 0:
                        # Store in database
                        from backend.repositories.ohlcv_repository import OHLCVRepository
                        repo = OHLCVRepository()
                        
                        # Add symbol and timeframe to each candle
                        formatted_candles = []
                        for candle in candles:
                            formatted_candles.append({
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'timestamp': candle['timestamp'],
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
                        
                        # Save in batch
                        count = repo.save_batch(formatted_candles)
                        logger.info(f"✓ Stored {count} candles for {symbol} {timeframe}")
                    else:
                        logger.warning(f"No data retrieved for {symbol} {timeframe}")
                except Exception as e:
                    logger.error(f"Error fetching {symbol} {timeframe}: {e}")
                    import traceback
                    traceback.print_exc()
        
        logger.info("Initial data population completed!")
        
        # Verify data was stored
        logger.info("Verifying stored data...")
        for symbol in symbols:
            for timeframe in timeframes:
                df = market_data_service.load_ohlcv_data(symbol, timeframe, limit=10)
                if df is not None and not df.empty:
                    logger.info(f"✓ Verified {symbol} {timeframe}: {len(df)} candles available")
                else:
                    logger.warning(f"⚠ No data found for {symbol} {timeframe}")
    
    except Exception as e:
        logger.error(f"Error in initial data population: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = asyncio.run(populate_initial_data())
    sys.exit(0 if success else 1)
