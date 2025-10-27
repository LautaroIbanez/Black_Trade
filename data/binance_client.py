"""Binance API client with authentication and candle data fetching."""
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging

logger = logging.getLogger(__name__)


class BinanceClient:
    """Client for interacting with Binance API."""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """Initialize Binance client with credentials."""
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        
        # Initialize client without credentials for public data access
        if not self.api_key or not self.api_secret:
            logger.warning("No credentials provided, using public API only")
            self.client = Client()
        else:
            self.client = Client(self.api_key, self.api_secret)
        
        logger.info("Binance client initialized")
    
    def get_historical_candles(self, symbol: str, interval: str, start_time: str = None, 
                               end_time: str = None, limit: int = 1000) -> List[Dict]:
        """Fetch historical candle data from Binance."""
        try:
            candles = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time,
                limit=limit
            )
            return self._format_candles(candles)
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            raise
    
    def _format_candles(self, candles: List[List]) -> List[Dict]:
        """Format raw Binance candles to standard OHLCV format."""
        formatted = []
        for candle in candles:
            formatted.append({
                'timestamp': int(candle[0]),
                'datetime': datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5]),
                'close_time': int(candle[6]),
                'quote_volume': float(candle[7]),
                'trades': int(candle[8]),
                'taker_buy_base': float(candle[9]),
                'taker_buy_quote': float(candle[10])
            })
        return formatted
    
    def get_server_time(self) -> int:
        """Get Binance server time."""
        try:
            server_time = self.client.get_server_time()
            return server_time['serverTime']
        except BinanceAPIException as e:
            logger.error(f"Error getting server time: {e}")
            raise
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            logger.error(f"Error getting current price: {e}")
            raise

