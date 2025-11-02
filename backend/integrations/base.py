"""Base interface for exchange adapters."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime


class ExchangeAdapter(ABC):
    """Base interface for exchange adapters."""
    
    @abstractmethod
    def get_balance(self, asset: Optional[str] = None) -> Dict[str, float]:
        """
        Get account balance.
        
        Args:
            asset: Specific asset to get balance for (None = all assets)
            
        Returns:
            Dictionary mapping asset to balance (free, locked, total)
        """
        pass
    
    @abstractmethod
    def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open positions.
        
        Args:
            symbol: Specific symbol to get positions for (None = all symbols)
            
        Returns:
            List of position dictionaries with keys:
            - symbol: Trading pair
            - side: 'long' or 'short'
            - size: Position size
            - entry_price: Entry price
            - current_price: Current market price
            - unrealized_pnl: Unrealized P&L
            - leverage: Leverage (if applicable)
        """
        pass
    
    @abstractmethod
    def get_fills(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """
        Get recent fills/trades.
        
        Args:
            symbol: Specific symbol to get fills for (None = all symbols)
            limit: Maximum number of fills to return
            
        Returns:
            List of fill dictionaries with keys:
            - symbol: Trading pair
            - side: 'buy' or 'sell'
            - size: Trade size
            - price: Execution price
            - fee: Fee paid
            - timestamp: Fill timestamp
        """
        pass
    
    @abstractmethod
    def get_account_status(self) -> Dict:
        """
        Get overall account status.
        
        Returns:
            Dictionary with:
            - total_capital: Total account value
            - available_capital: Available for trading
            - margin_used: Margin currently used (if applicable)
            - unrealized_pnl: Total unrealized P&L
            - equity: Account equity (capital + unrealized_pnl)
        """
        pass
    
    @abstractmethod
    def subscribe_to_updates(self, callback) -> None:
        """
        Subscribe to real-time updates via WebSocket.
        
        Args:
            callback: Function to call when updates are received
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from exchange."""
        pass

