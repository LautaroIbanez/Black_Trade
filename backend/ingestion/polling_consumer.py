"""REST polling consumer as fallback for WebSocket."""
import asyncio
import logging
from typing import List, Callable, Optional, Dict
from datetime import datetime

from data.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class PollingConsumer:
    """REST polling consumer for fetching latest candles."""
    
    def __init__(self, symbols: List[str], timeframes: List[str],
                 message_callback: Callable, 
                 polling_intervals: Optional[Dict[str, int]] = None):
        """
        Initialize polling consumer.
        
        Args:
            symbols: List of trading pairs
            timeframes: List of intervals
            message_callback: Callback for processed candles
            polling_intervals: Dict mapping timeframe to polling interval in seconds
        """
        self.binance_client = BinanceClient()
        self.symbols = symbols
        self.timeframes = timeframes
        self.message_callback = message_callback
        self.running = False
        
        # Default polling intervals (in seconds)
        default_intervals = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400,
        }
        
        self.polling_intervals = polling_intervals or {}
        for tf in self.timeframes:
            if tf not in self.polling_intervals:
                self.polling_intervals[tf] = default_intervals.get(tf, 3600)
        
        # Track last processed timestamps per symbol/timeframe
        self.last_timestamps = {}
    
    async def _fetch_and_process(self, symbol: str, timeframe: str):
        """Fetch latest candles and process new ones."""
        try:
            # Get last processed timestamp
            key = f"{symbol}_{timeframe}"
            last_ts = self.last_timestamps.get(key, 0)
            
            # Fetch latest candles (limit 100)
            candles = self.binance_client.get_historical_candles(
                symbol=symbol,
                interval=timeframe,
                limit=100
            )
            
            if not candles:
                return
            
            # Filter for new candles (timestamp > last_ts)
            new_candles = [c for c in candles if c['timestamp'] > last_ts]
            
            # Process new candles
            for candle in new_candles:
                # Only process closed candles (current candle may still be forming)
                # We check by comparing with previous candles or using a heuristic
                await self.message_callback(candle)
                
                # Update last timestamp
                if candle['timestamp'] > last_ts:
                    self.last_timestamps[key] = candle['timestamp']
            
            if new_candles:
                logger.info(f"Processed {len(new_candles)} new candles for {symbol} {timeframe}")
                
        except Exception as e:
            logger.error(f"Error fetching/processing {symbol} {timeframe}: {e}")
    
    async def _poll_timeframe(self, symbol: str, timeframe: str):
        """Poll a specific symbol/timeframe continuously."""
        interval = self.polling_intervals[timeframe]
        
        while self.running:
            try:
                await self._fetch_and_process(symbol, timeframe)
            except Exception as e:
                logger.error(f"Error in polling loop for {symbol} {timeframe}: {e}")
            
            await asyncio.sleep(interval)
    
    async def start(self):
        """Start polling for all symbol/timeframe combinations."""
        self.running = True
        
        # Create tasks for each combination
        tasks = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                task = asyncio.create_task(self._poll_timeframe(symbol, timeframe))
                tasks.append(task)
        
        logger.info(f"Started polling for {len(tasks)} symbol/timeframe combinations")
        
        # Wait for all tasks
        await asyncio.gather(*tasks)
    
    def stop(self):
        """Stop polling."""
        self.running = False
        logger.info("Polling consumer stopped")


async def test_polling():
    """Test function for polling consumer."""
    async def callback(candle):
        print(f"Received candle: {candle['symbol']} {candle.get('timeframe', 'N/A')} @ {candle['timestamp']}")
    
    consumer = PollingConsumer(
        symbols=['BTCUSDT'],
        timeframes=['1h'],
        message_callback=callback,
        polling_intervals={'1h': 10}  # Test with 10s interval
    )
    
    # Run for 30 seconds
    await asyncio.wait_for(consumer.start(), timeout=30)


if __name__ == '__main__':
    asyncio.run(test_polling())

