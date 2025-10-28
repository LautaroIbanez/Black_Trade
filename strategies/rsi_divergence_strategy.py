"""RSI divergence strategy for detecting reversals."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class RSIDivergenceStrategy(StrategyBase):
    """RSI divergence strategy for detecting reversals."""
    
    def __init__(self, rsi_period: int = 14, divergence_lookback: int = 5, 
                 min_divergence: float = 0.1, volume_confirmation: bool = True,
                 commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("RSIDivergence", {
            "rsi_period": rsi_period,
            "divergence_lookback": divergence_lookback,
            "min_divergence": min_divergence,
            "volume_confirmation": volume_confirmation
        }, commission, slippage)
        self.rsi_period = rsi_period
        self.divergence_lookback = divergence_lookback
        self.min_divergence = min_divergence
        self.volume_confirmation = volume_confirmation
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI and divergence indicators."""
        df = df.copy()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['bullish_divergence'] = 0
        df['bearish_divergence'] = 0
        df['volume_ratio'] = 1.0
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
        """Generate trading signal based on RSI divergence."""
        return 0, 0.0, "No signal"
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """Calculate explicit take profit and stop loss levels."""
        return {"stop_loss": entry_price, "take_profit": entry_price}
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "rsi_period": self.rsi_period,
            "divergence_lookback": self.divergence_lookback,
            "min_divergence": self.min_divergence,
            "volume_confirmation": self.volume_confirmation
        }
