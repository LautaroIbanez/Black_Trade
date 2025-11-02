"""WebSocket consumer for real-time Binance kline streams."""
import asyncio
import json
import logging
import time
from typing import Callable, Optional, List
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

logger = logging.getLogger(__name__)


class BinanceWebSocketConsumer:
    """WebSocket consumer for Binance kline streams."""
    
    BASE_URL = "wss://stream.binance.com:9443/ws/"
    
    def __init__(self, symbols: List[str], timeframes: List[str], 
                 message_callback: Callable, reconnect_delay: int = 5):
        """
        Initialize WebSocket consumer.
        
        Args:
            symbols: List of trading pairs (e.g., ['btcusdt', 'ethusdt'])
            timeframes: List of intervals (e.g., ['1m', '5m', '1h'])
            message_callback: Callback function to process received messages
            reconnect_delay: Initial delay before reconnection (seconds)
        """
        self.symbols = [s.lower() for s in symbols]
        self.timeframes = timeframes
        self.message_callback = message_callback
        self.reconnect_delay = reconnect_delay
        self.websocket = None
        self.running = False
        self.reconnect_count = 0
        self.max_reconnect_delay = 60
        
        # Build stream names
        self.streams = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                stream_name = f"{symbol}@kline_{timeframe}"
                self.streams.append(stream_name)
    
    def _build_stream_url(self) -> str:
        """Build WebSocket stream URL."""
        if len(self.streams) == 1:
            # Single stream
            return f"{self.BASE_URL}{self.streams[0]}"
        else:
            # Multiple streams (use combined stream)
            stream_params = "/".join(self.streams)
            return f"wss://stream.binance.com:9443/stream?streams={stream_params}"
    
    async def connect(self):
        """Connect to WebSocket stream."""
        url = self._build_stream_url()
        logger.info(f"Connecting to Binance WebSocket: {url}")
        
        try:
            self.websocket = await websockets.connect(url, ping_interval=20, ping_timeout=10)
            self.reconnect_count = 0
            logger.info("WebSocket connected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket disconnected")
    
    def _parse_kline_message(self, message: dict) -> Optional[dict]:
        """Parse Binance kline WebSocket message."""
        try:
            # Handle combined stream format
            if 'stream' in message and 'data' in message:
                stream = message['stream']
                data = message['data']
            else:
                # Single stream format
                data = message
            
            if 'k' not in data:
                return None
            
            kline = data['k']
            
            # Extract candle data
            candle = {
                'symbol': kline['s'],
                'timeframe': self._extract_timeframe_from_stream(stream if 'stream' in message else None),
                'timestamp': kline['t'],  # Open time
                'open': float(kline['o']),
                'high': float(kline['h']),
                'low': float(kline['l']),
                'close': float(kline['c']),
                'volume': float(kline['v']),
                'quote_volume': float(kline.get('q', 0)),
                'trades': int(kline.get('n', 0)),
                'taker_buy_base': float(kline.get('V', 0)),
                'taker_buy_quote': float(kline.get('Q', 0)),
                'close_time': kline['T'],
                'is_closed': kline['x'],  # Whether this kline is closed
            }
            
            return candle
        except Exception as e:
            logger.error(f"Error parsing kline message: {e}")
            return None
    
    def _extract_timeframe_from_stream(self, stream: Optional[str]) -> str:
        """Extract timeframe from stream name."""
        if stream:
            # Format: btcusdt@kline_1m
            parts = stream.split('@kline_')
            if len(parts) == 2:
                return parts[1]
        # Fallback: return first timeframe
        return self.timeframes[0]
    
    async def _handle_message(self, raw_message: str):
        """Handle incoming WebSocket message."""
        try:
            message = json.loads(raw_message)
            candle = self._parse_kline_message(message)
            
            if candle:
                # Only process closed candles (x=True)
                if candle.get('is_closed', False):
                    await self.message_callback(candle)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message as JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _reconnect(self):
        """Reconnect with exponential backoff."""
        delay = min(self.reconnect_delay * (2 ** self.reconnect_count), self.max_reconnect_delay)
        self.reconnect_count += 1
        
        logger.warning(f"Reconnecting in {delay} seconds (attempt {self.reconnect_count})...")
        await asyncio.sleep(delay)
        
        return await self.connect()
    
    async def run(self):
        """Run the WebSocket consumer."""
        self.running = True
        
        while self.running:
            try:
                if not self.websocket or self.websocket.closed:
                    connected = await self.connect()
                    if not connected:
                        await self._reconnect()
                        continue
                
                # Receive messages
                async for message in self.websocket:
                    if not self.running:
                        break
                    await self._handle_message(message)
                    
            except ConnectionClosed:
                logger.warning("WebSocket connection closed")
                if self.running:
                    await self._reconnect()
            except InvalidStatusCode as e:
                logger.error(f"Invalid WebSocket status code: {e}")
                if self.running:
                    await asyncio.sleep(self.reconnect_delay)
                    await self._reconnect()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.running:
                    await self._reconnect()
    
    async def start(self):
        """Start the consumer (non-blocking)."""
        await self.run()


async def test_consumer():
    """Test function for WebSocket consumer."""
    def callback(candle):
        print(f"Received candle: {candle['symbol']} {candle['timeframe']} @ {candle['timestamp']}")
    
    consumer = BinanceWebSocketConsumer(
        symbols=['btcusdt'],
        timeframes=['1m'],
        message_callback=callback
    )
    
    await consumer.start()


if __name__ == '__main__':
    asyncio.run(test_consumer())

