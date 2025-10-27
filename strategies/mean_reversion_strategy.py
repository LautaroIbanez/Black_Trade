"""Mean Reversion with Multi-Indicator Confirmation Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class MeanReversionStrategy(StrategyBase):
    """Mean reversion with multi-indicator confirmation."""
    
    def __init__(self, period: int = 20, bb_std: float = 2.0, rsi_period: int = 14):
        super().__init__("Mean_Reversion", {"period": period, "bb_std": bb_std, "rsi": rsi_period})
        self.period = period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate mean reversion signals."""
        df = df.copy()
        df['sma'] = df['close'].rolling(window=self.period).mean()
        df['std'] = df['close'].rolling(window=self.period).std()
        df['upper_band'] = df['sma'] + (self.bb_std * df['std'])
        df['lower_band'] = df['sma'] - (self.bb_std * df['std'])
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['signal'] = 0
        df.loc[(df['close'] <= df['lower_band']) & (df['rsi'] < 30), 'signal'] = 1
        df.loc[(df['close'] >= df['upper_band']) & (df['rsi'] > 70), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from mean reversion signals."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = 'long' if row['signal'] == 1 else 'short'
                entry_price = row['close']
                entry_idx = idx
            elif position:
                target = df.loc[idx, 'sma']
                if (position == 'long' and row['close'] >= target) or (position == 'short' and row['close'] <= target):
                    pnl = (row['close'] - entry_price) if position == 'long' else (entry_price - row['close'])
                    trades.append({"entry_price": entry_price, "exit_price": row['close'], "side": position, "pnl": pnl, "entry_time": df.loc[entry_idx, 'timestamp'], "exit_time": row['timestamp']})
                    position = None
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

