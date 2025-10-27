"""Momentum Strategy with Multi-Timeframe Confirmation."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class MomentumStrategy(StrategyBase):
    """Momentum strategy with multi-timeframe confirmation."""
    
    def __init__(self, rsi_period: int = 14, macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9):
        super().__init__("Momentum", {"rsi": rsi_period, "macd_fast": macd_fast, "macd_slow": macd_slow, "macd_signal": macd_signal})
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate momentum signals."""
        df = df.copy()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['signal'] = 0
        df.loc[(df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1)) & (df['rsi'] > 50), 'signal'] = 1
        df.loc[(df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1)) & (df['rsi'] < 50), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from momentum signals."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = 'long' if row['signal'] == 1 else 'short'
                entry_price = row['close']
                entry_idx = idx
            elif position and row['signal'] != 0:
                pnl = (row['close'] - entry_price) if position == 'long' else (entry_price - row['close'])
                trades.append({"entry_price": entry_price, "exit_price": row['close'], "side": position, "pnl": pnl, "entry_time": df.loc[entry_idx, 'timestamp'], "exit_time": row['timestamp']})
                position = 'long' if row['signal'] == 1 else 'short' if row['signal'] == -1 else None
                entry_price = row['close']
                entry_idx = idx
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


