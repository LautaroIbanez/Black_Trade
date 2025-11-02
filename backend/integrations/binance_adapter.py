"""Binance exchange adapter for account data."""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import websockets
import json

from binance.client import Client
from binance.exceptions import BinanceAPIException

from backend.integrations.base import ExchangeAdapter

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """Binance exchange adapter for spot trading."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, testnet: bool = False):
        """
        Initialize Binance adapter.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (default: False)
        """
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        self.testnet = testnet
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Binance API credentials required")
        
        # Initialize client
        if testnet:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=True
            )
        else:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret
            )
        
        self.ws_stream = None
        self.ws_task = None
        logger.info(f"Binance adapter initialized (testnet={testnet})")
    
    def get_balance(self, asset: Optional[str] = None) -> Dict[str, float]:
        """Get account balance."""
        try:
            account = self.client.get_account()
            balances = {}
            
            for balance in account['balances']:
                asset_name = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                
                if free > 0 or locked > 0:
                    balances[asset_name] = {
                        'free': free,
                        'locked': locked,
                        'total': free + locked,
                    }
            
            if asset:
                return balances.get(asset, {'free': 0.0, 'locked': 0.0, 'total': 0.0})
            
            return balances
        except BinanceAPIException as e:
            logger.error(f"Error getting balance: {e}")
            raise
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open positions (spot positions = balances with non-zero values)."""
        try:
            # For spot trading, positions are non-zero balances
            balances = self.get_balance()
            positions = []
            
            # Get current prices for all assets with balances
            tickers = self.client.get_all_tickers()
            price_map = {t['symbol']: float(t['price']) for t in tickers}
            
            # Get USDT balance for reference
            usdt_balance = balances.get('USDT', {}).get('total', 0.0)
            total_capital = usdt_balance
            
            # For each non-USDT asset with balance, treat as a position
            for asset, balance_info in balances.items():
                if asset == 'USDT' or balance_info['total'] <= 0:
                    continue
                
                # Find trading pair (e.g., BTCUSDT)
                trading_pair = f"{asset}USDT"
                if trading_pair not in price_map:
                    continue
                
                current_price = price_map[trading_pair]
                size = balance_info['total']
                
                # Calculate entry price (simplified: assume current price)
                # In production, would track actual entry prices
                entry_price = current_price
                
                # Calculate unrealized PnL (simplified)
                unrealized_pnl = (current_price - entry_price) * size
                
                positions.append({
                    'symbol': trading_pair,
                    'asset': asset,
                    'side': 'long',  # Spot is always long
                    'size': size,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'unrealized_pnl': unrealized_pnl,
                    'leverage': 1.0,  # Spot has no leverage
                    'usd_value': size * current_price,
                })
                
                total_capital += size * current_price
            
            if symbol:
                return [p for p in positions if p['symbol'] == symbol]
            
            return positions
        except BinanceAPIException as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent fills/trades."""
        try:
            # Get recent trades
            if symbol:
                trades = self.client.get_my_trades(symbol=symbol, limit=limit)
            else:
                # Get all recent trades (limited to most recent symbols)
                trades = []
                # Would need to iterate through symbols or use a different approach
                # For now, return empty if no symbol specified
                return []
            
            fills = []
            for trade in trades:
                fills.append({
                    'symbol': trade['symbol'],
                    'side': trade['isBuyer'] and 'buy' or 'sell',
                    'size': float(trade['qty']),
                    'price': float(trade['price']),
                    'fee': float(trade.get('commission', 0)),
                    'fee_asset': trade.get('commissionAsset', ''),
                    'timestamp': datetime.fromtimestamp(trade['time'] / 1000),
                    'trade_id': trade['id'],
                })
            
            return fills
        except BinanceAPIException as e:
            logger.error(f"Error getting fills: {e}")
            raise
    
    def get_account_status(self) -> Dict:
        """Get overall account status."""
        try:
            balance = self.get_balance()
            positions = self.get_positions()
            
            # Calculate total capital
            usdt_balance = balance.get('USDT', {}).get('total', 0.0)
            positions_value = sum(p['usd_value'] for p in positions)
            total_capital = usdt_balance + positions_value
            
            # Calculate unrealized PnL
            unrealized_pnl = sum(p['unrealized_pnl'] for p in positions)
            
            # Equity = capital + unrealized PnL
            equity = total_capital + unrealized_pnl
            
            return {
                'total_capital': total_capital,
                'available_capital': usdt_balance,
                'margin_used': 0.0,  # Spot has no margin
                'unrealized_pnl': unrealized_pnl,
                'equity': equity,
                'positions_count': len(positions),
                'last_updated': datetime.now().isoformat(),
            }
        except BinanceAPIException as e:
            logger.error(f"Error getting account status: {e}")
            raise
    
    async def subscribe_to_updates(self, callback) -> None:
        """Subscribe to real-time account updates via WebSocket."""
        # Binance User Data Stream
        listen_key = self.client.stream_get_listen_key()
        ws_url = f"wss://stream.binance.com:9443/ws/{listen_key}"
        
        async def listen_stream():
            try:
                async with websockets.connect(ws_url) as websocket:
                    self.ws_stream = websocket
                    async for message in websocket:
                        data = json.loads(message)
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                # Reconnect logic would go here
        
        self.ws_task = asyncio.create_task(listen_stream())
    
    def disconnect(self) -> None:
        """Disconnect from exchange."""
        if self.ws_task:
            self.ws_task.cancel()
        if self.ws_stream:
            asyncio.create_task(self.ws_stream.close())
        
        # Invalidate listen key
        try:
            self.client.stream_close_listen_key()
        except:
            pass

