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
        
        # MACD crossover signals
        df.loc[df['macd'] > df['macd_signal'], 'signal'] = 1
        df.loc[df['macd'] < df['macd_signal'], 'signal'] = -1
        
        # Zero line cross confirmation
        if self.zero_line_cross:
            df.loc[df['macd'] <= 0, 'signal'] = 0
            df.loc[df['macd'] >= 0, 'signal'] = 0
        
        # Histogram confirmation
        df.loc[abs(df['macd_histogram']) < self.histogram_threshold, 'signal'] = 0
        
        # Calculate signal strength based on histogram magnitude
        df['strength'] = abs(df['macd_histogram']) / df['macd_histogram'].rolling(20).std()
        df['strength'] = df['strength'].fillna(0)
        df['strength'] = np.clip(df['strength'], 0, 1)
        
        # Generate reasons
        df.loc[df['signal'] == 1, 'reason'] = "MACD bullish crossover"
        df.loc[df['signal'] == -1, 'reason'] = "MACD bearish crossover"
        
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trade list from signals."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
            elif position and row['signal'] != 0 and row['signal'] != (1 if position['side'] == 'long' else -1):
                # Signal change - close position and open new one
                exit_price = row['close']
                pnl = (exit_price - entry_price) if position['side'] == 'long' else (entry_price - exit_price)
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "side": position['side'],
                    "pnl": pnl,
                    "entry_time": position['entry_time'],
                    "exit_time": row['timestamp']
                })
                
                # Open new position
                position = {
                    'side': 'long' if row['signal'] == 1 else 'short',
                    'entry_price': row['close'],
                    'entry_idx': idx,
                    'entry_time': row['timestamp']
                }
                entry_price = row['close']
                entry_idx = idx
        
        # Close final position if exists
        if position:
            final_trade = self.close_all_positions(df, position, df.iloc[-1]['close'], len(df) - 1)
            if final_trade:
                trades.append(final_trade)
        
        return trades
    
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
