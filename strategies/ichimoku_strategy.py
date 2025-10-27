"""Ichimoku Cloud + ADX Confirmation Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class IchimokuStrategy(StrategyBase):
    """Ichimoku Cloud + ADX confirmation strategy."""
    
    def __init__(self, conversion_period: int = 9, base_period: int = 26, leading_span_b: int = 52, displacement: int = 26, adx_period: int = 14, adx_threshold: int = 25):
        super().__init__("Ichimoku_ADX", {"conversion": conversion_period, "base": base_period, "leading_b": leading_span_b, "displacement": displacement, "adx": adx_period})
        self.conversion_period = conversion_period
        self.base_period = base_period
        self.leading_span_b = leading_span_b
        self.displacement = displacement
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on Ichimoku cloud and ADX."""
        df = df.copy()
        high_9 = df['high'].rolling(window=self.conversion_period).max()
        low_9 = df['low'].rolling(window=self.conversion_period).min()
        df['tenkan_sen'] = (high_9 + low_9) / 2
        high_26 = df['high'].rolling(window=self.base_period).max()
        low_26 = df['low'].rolling(window=self.base_period).min()
        df['kijun_sen'] = (high_26 + low_26) / 2
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(self.displacement)
        high_52 = df['high'].rolling(window=self.leading_span_b).max()
        low_52 = df['low'].rolling(window=self.leading_span_b).min()
        df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(self.displacement)
        df['adx'] = self._calculate_adx(df, self.adx_period)
        df['signal'] = 0
        df.loc[(df['close'] > df['senkou_span_a']) & (df['close'] > df['senkou_span_b']) & (df['tenkan_sen'] > df['kijun_sen']) & (df['adx'] > self.adx_threshold), 'signal'] = 1
        df.loc[(df['close'] < df['senkou_span_a']) & (df['close'] < df['senkou_span_b']) & (df['tenkan_sen'] < df['kijun_sen']) & (df['adx'] > self.adx_threshold), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from signals."""
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
    
    def _calculate_adx(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate ADX indicator."""
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return adx

