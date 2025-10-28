"""Stochastic oscillator strategy with divergence detection."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from .strategy_base import StrategyBase


class StochasticStrategy(StrategyBase):
    """Stochastic oscillator strategy with divergence detection."""
    
    def __init__(self, k_period: int = 14, d_period: int = 3, smooth_k: int = 3,
                 overbought: float = 80, oversold: float = 20, divergence_lookback: int = 5,
                 commission: float = 0.001, slippage: float = 0.0005):
        super().__init__("Stochastic", {
            "k_period": k_period,
            "d_period": d_period,
            "smooth_k": smooth_k,
            "overbought": overbought,
            "oversold": oversold,
            "divergence_lookback": divergence_lookback
        }, commission, slippage)
        self.k_period = k_period
        self.d_period = d_period
        self.smooth_k = smooth_k
        self.overbought = overbought
        self.oversold = oversold
        self.divergence_lookback = divergence_lookback
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Stochastic indicators."""
        df = df.copy()
        lowest_low = df['low'].rolling(window=self.k_period).min()
        highest_high = df['high'].rolling(window=self.k_period).max()
        df['stoch_k'] = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low)
        df['stoch_k_smooth'] = df['stoch_k'].rolling(window=self.smooth_k).mean()
        df['stoch_d'] = df['stoch_k_smooth'].rolling(window=self.d_period).mean()
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from price data."""
        df = self.calculate_indicators(df)
        df['signal'] = 0
        df['strength'] = 0.0
        df['reason'] = "No signal"
        
        # Stochastic crossover signals
        df.loc[df['stoch_k_smooth'] > df['stoch_d'], 'signal'] = 1
        df.loc[df['stoch_k_smooth'] < df['stoch_d'], 'signal'] = -1
        
        # Overbought/oversold confirmation
        df.loc[df['stoch_k_smooth'] > self.overbought, 'signal'] = -1
        df.loc[df['stoch_k_smooth'] < self.oversold, 'signal'] = 1
        
        # Calculate signal strength based on distance from overbought/oversold levels
        df['strength'] = 0.0
        df.loc[df['signal'] == 1, 'strength'] = (self.oversold - df['stoch_k_smooth']) / self.oversold
        df.loc[df['signal'] == -1, 'strength'] = (df['stoch_k_smooth'] - self.overbought) / (100 - self.overbought)
        df['strength'] = np.clip(df['strength'], 0, 1)
        
        # Generate reasons
        df.loc[df['signal'] == 1, 'reason'] = "Stochastic bullish crossover"
        df.loc[df['signal'] == -1, 'reason'] = "Stochastic bearish crossover"
        
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
        """Generate trading signal based on Stochastic oscillator."""
        return 0, 0.0, "No signal"
    
    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        """Calculate explicit take profit and stop loss levels."""
        return {"stop_loss": entry_price, "take_profit": entry_price}
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            "k_period": self.k_period,
            "d_period": self.d_period,
            "smooth_k": self.smooth_k,
            "overbought": self.overbought,
            "oversold": self.oversold,
            "divergence_lookback": self.divergence_lookback
        }
