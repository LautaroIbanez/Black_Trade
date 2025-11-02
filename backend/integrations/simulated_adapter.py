"""Simulated exchange adapter for paper trading."""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from backend.integrations.base import ExchangeAdapter

logger = logging.getLogger(__name__)


class SimulatedAdapter(ExchangeAdapter):
    """Simulated exchange adapter for paper trading and testing."""
    
    def __init__(self, initial_capital: float = 10000.0, base_asset: str = 'USDT'):
        """
        Initialize simulated adapter.
        
        Args:
            initial_capital: Starting capital in base asset
            base_asset: Base asset (default: USDT)
        """
        self.initial_capital = initial_capital
        self.base_asset = base_asset
        self.balances = {base_asset: {'free': initial_capital, 'locked': 0.0, 'total': initial_capital}}
        self.positions = []  # Track positions
        self.fills = []  # Track all fills
        self.peak_equity = initial_capital
        self.logger = logging.getLogger(__name__)
    
    def get_balance(self, asset: Optional[str] = None) -> Dict[str, float]:
        """Get account balance."""
        if asset:
            return self.balances.get(asset, {'free': 0.0, 'locked': 0.0, 'total': 0.0})
        return self.balances.copy()
    
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open positions."""
        if symbol:
            return [p for p in self.positions if p['symbol'] == symbol]
        return self.positions.copy()
    
    def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get recent fills."""
        fills = self.fills[-limit:] if len(self.fills) > limit else self.fills
        if symbol:
            fills = [f for f in fills if f['symbol'] == symbol]
        return fills
    
    def get_account_status(self) -> Dict:
        """Get overall account status."""
        # Calculate total capital
        base_balance = self.balances.get(self.base_asset, {}).get('total', 0.0)
        positions_value = sum(p.get('usd_value', 0) for p in self.positions)
        total_capital = base_balance + positions_value
        
        # Calculate unrealized PnL
        unrealized_pnl = sum(p.get('unrealized_pnl', 0) for p in self.positions)
        
        # Equity
        equity = total_capital + unrealized_pnl
        
        # Update peak
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        return {
            'total_capital': total_capital,
            'available_capital': base_balance,
            'margin_used': 0.0,
            'unrealized_pnl': unrealized_pnl,
            'equity': equity,
            'peak_equity': self.peak_equity,
            'positions_count': len(self.positions),
            'last_updated': datetime.now().isoformat(),
        }
    
    def subscribe_to_updates(self, callback) -> None:
        """Simulated adapter doesn't support WebSocket updates."""
        logger.warning("Simulated adapter doesn't support real-time WebSocket updates")
    
    def disconnect(self) -> None:
        """Disconnect (no-op for simulated)."""
        pass
    
    def simulate_fill(self, symbol: str, side: str, size: float, price: float, fee: float = 0.001):
        """Simulate a trade fill (for testing)."""
        asset = symbol.replace('USDT', '')
        base = self.base_asset
        
        fill = {
            'symbol': symbol,
            'side': side,
            'size': size,
            'price': price,
            'fee': fee,
            'fee_asset': base,
            'timestamp': datetime.now(),
            'trade_id': len(self.fills) + 1,
        }
        
        self.fills.append(fill)
        
        # Update balances and positions
        if side == 'buy':
            # Buy asset with base
            cost = size * price * (1 + fee)
            if self.balances[base]['free'] >= cost:
                self.balances[base]['free'] -= cost
                self.balances[base]['total'] -= cost
                
                if asset not in self.balances:
                    self.balances[asset] = {'free': 0.0, 'locked': 0.0, 'total': 0.0}
                
                self.balances[asset]['free'] += size
                self.balances[asset]['total'] += size
                
                # Update or create position
                existing = next((p for p in self.positions if p['symbol'] == symbol), None)
                if existing:
                    # Average entry price
                    total_cost = existing['size'] * existing['entry_price'] + cost
                    total_size = existing['size'] + size
                    existing['entry_price'] = total_cost / total_size
                    existing['size'] = total_size
                    existing['usd_value'] = total_size * price
                else:
                    self.positions.append({
                        'symbol': symbol,
                        'asset': asset,
                        'side': 'long',
                        'size': size,
                        'entry_price': price,
                        'current_price': price,
                        'unrealized_pnl': 0.0,
                        'leverage': 1.0,
                        'usd_value': size * price,
                    })
        else:
            # Sell asset for base
            proceeds = size * price * (1 - fee)
            if asset in self.balances and self.balances[asset]['free'] >= size:
                self.balances[asset]['free'] -= size
                self.balances[asset]['total'] -= size
                
                self.balances[base]['free'] += proceeds
                self.balances[base]['total'] += proceeds
                
                # Reduce or close position
                existing = next((p for p in self.positions if p['symbol'] == symbol), None)
                if existing:
                    existing['size'] -= size
                    if existing['size'] <= 0:
                        self.positions.remove(existing)
                    else:
                        existing['usd_value'] = existing['size'] * price
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update current price for a position (for PnL calculation)."""
        for position in self.positions:
            if position['symbol'] == symbol:
                position['current_price'] = current_price
                position['unrealized_pnl'] = (current_price - position['entry_price']) * position['size']
                position['usd_value'] = position['size'] * current_price
                break

