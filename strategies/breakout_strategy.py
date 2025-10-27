"""Volatility Breakout with Trailing Stop Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class BreakoutStrategy(StrategyBase):
    """Volatility breakout with trailing stop strategy."""
    
    def __init__(self, lookback: int = 20, multiplier: float = 2.0, trailing_percent: float = 0.01):
        super().__init__("Breakout", {"lookback": lookback, "multiplier": multiplier, "trailing": trailing_percent})
        self.lookback = lookback
        self.multiplier = multiplier
        self.trailing_percent = trailing_percent
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate breakout signals."""
        df = df.copy()
        df['high_max'] = df['high'].rolling(window=self.lookback).max()
        df['low_min'] = df['low'].rolling(window=self.lookback).min()
        df['atr'] = self._calculate_atr(df, 14)
        df['upper_band'] = df['close'].rolling(window=self.lookback).mean() + (self.multiplier * df['atr'])
        df['lower_band'] = df['close'].rolling(window=self.lookback).mean() - (self.multiplier * df['atr'])
        df['signal'] = 0
        df.loc[df['close'] > df['upper_band'], 'signal'] = 1
        df.loc[df['close'] < df['lower_band'], 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades with trailing stop."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        trailing_stop = 0
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = 'long' if row['signal'] == 1 else 'short'
                entry_price = row['close']
                entry_idx = idx
                trailing_stop = entry_price * (1 - self.trailing_percent) if position == 'long' else entry_price * (1 + self.trailing_percent)
            elif position == 'long':
                if row['low'] <= trailing_stop:
                    pnl = trailing_stop - entry_price
                    trades.append({"entry_price": entry_price, "exit_price": trailing_stop, "side": position, "pnl": pnl, "entry_time": df.loc[entry_idx, 'timestamp'], "exit_time": row['timestamp']})
                    position = None
                else:
                    new_stop = row['close'] * (1 - self.trailing_percent)
                    trailing_stop = max(trailing_stop, new_stop)
            elif position == 'short':
                if row['high'] >= trailing_stop:
                    pnl = entry_price - trailing_stop
                    trades.append({"entry_price": entry_price, "exit_price": trailing_stop, "side": position, "pnl": pnl, "entry_time": df.loc[entry_idx, 'timestamp'], "exit_time": row['timestamp']})
                    position = None
                else:
                    new_stop = row['close'] * (1 + self.trailing_percent)
                    trailing_stop = min(trailing_stop, new_stop)
        return trades
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ATR indicator."""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

