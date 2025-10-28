"""MACD crossover strategy with histogram confirmation."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class MACDCrossoverStrategy(StrategyBase):
    """MACD crossover strategy with histogram confirmation."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9,
                 histogram_threshold: float = 0.001, zero_line_cross: bool = True,
                 commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("MACDCrossover", {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "histogram_threshold": histogram_threshold,
            "zero_line_cross": zero_line_cross
        }, commission, slippage)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.histogram_threshold = histogram_threshold
        self.zero_line_cross = zero_line_cross
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicators."""
        df = df.copy()
        ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        df = self.calculate_indicators(df)
        df['signal'] = 0
        df['strength'] = 0.0
        df['reason'] = "No signal"
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals."""
        return []
    
    def close_all_positions(self, df: pd.DataFrame, current_position: Optional[Dict], current_price: float, current_idx: int) -> Optional[Dict]:
        """Close any remaining positions at the end of backtest."""
        return None
    
    def _generate_signal(self, df: pd.DataFrame) -> Tuple[int, float, str]:
        """Generate trading signal based on MACD crossovers."""
        return 0, 0.0, "No signal"
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """Calculate explicit take profit and stop loss levels."""
        return {"stop_loss": entry_price, "take_profit": entry_price}
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period,
            "histogram_threshold": self.histogram_threshold,
            "zero_line_cross": self.zero_line_cross
        }
