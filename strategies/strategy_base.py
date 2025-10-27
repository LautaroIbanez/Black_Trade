"""Base strategy class for all trading strategies."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd


class StrategyBase(ABC):
    """Abstract base class for trading strategies."""
    
    def __init__(self, name: str, params: Dict[str, Any] = None):
        """Initialize strategy with name and parameters."""
        self.name = name
        self.params = params or {}
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        pass
    
    @abstractmethod
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals."""
        pass
    
    def backtest(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest and return metrics."""
        signals_df = self.generate_signals(df)
        trades = self.generate_trades(signals_df)
        return self._calculate_metrics(trades, df)
    
    def _calculate_metrics(self, trades: List[Dict], df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate backtest metrics from trades."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "net_pnl": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0
            }
        
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
        
        total_trades = len(trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        net_pnl = sum(t.get('pnl', 0) for t in trades)
        
        gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        
        # Calculate max drawdown
        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        
        for trade in trades:
            cumulative_pnl += trade.get('pnl', 0)
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "net_pnl": net_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
            "expectancy": expectancy
        }

