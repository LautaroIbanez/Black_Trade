"""EMA Crossover + RSI Filter Strategy."""
import pandas as pd
import numpy as np
from typing import List, Dict
from strategies.strategy_base import StrategyBase


class EMARSIStrategy(StrategyBase):
    """EMA Crossover with RSI filter strategy."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, rsi_period: int = 14, rsi_oversold: int = 30, rsi_overbought: int = 70):
        super().__init__("EMA_RSI", {"fast": fast_period, "slow": slow_period, "rsi": rsi_period})
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate signals based on EMA crossover and RSI."""
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['rsi'] = self._calculate_rsi(df['close'], self.rsi_period)
        df['signal'] = 0
        df.loc[(df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1)) & (df['rsi'] > self.rsi_oversold), 'signal'] = 1
        df.loc[(df['ema_fast'] < df['ema_slow']) & (df['ema_fast'].shift(1) >= df['ema_slow'].shift(1)) & (df['rsi'] < self.rsi_overbought), 'signal'] = -1
        return df
    
    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trades from signals with stop loss and take profit."""
        trades = []
        position = None
        entry_price = 0
        entry_idx = 0
        stop_loss_pct = 0.02
        take_profit_pct = 0.04
        
        for idx, row in df.iterrows():
            if position is None and row['signal'] != 0:
                position = 'long' if row['signal'] == 1 else 'short'
                entry_price = row['close']
                entry_idx = idx
                sl = entry_price * (1 - stop_loss_pct) if position == 'long' else entry_price * (1 + stop_loss_pct)
                tp = entry_price * (1 + take_profit_pct) if position == 'long' else entry_price * (1 - take_profit_pct)
            elif position:
                exit_price = row['close']
                sl_hit = (position == 'long' and row['low'] <= sl) or (position == 'short' and row['high'] >= sl)
                tp_hit = (position == 'long' and row['high'] >= tp) or (position == 'short' and row['low'] <= tp)
                
                if sl_hit or tp_hit or row['signal'] != 0:
                    if sl_hit:
                        exit_price = sl
                    elif tp_hit:
                        exit_price = tp
                    pnl = (exit_price - entry_price) if position == 'long' else (entry_price - exit_price)
                    trades.append({"entry_price": entry_price, "exit_price": exit_price, "side": position, "pnl": pnl, "entry_time": df.loc[entry_idx, 'timestamp'], "exit_time": row['timestamp']})
                    position = None
                    if row['signal'] != 0:
                        position = 'long' if row['signal'] == 1 else 'short'
                        entry_price = row['close']
                        entry_idx = idx
                        sl = entry_price * (1 - stop_loss_pct) if position == 'long' else entry_price * (1 + stop_loss_pct)
                        tp = entry_price * (1 + take_profit_pct) if position == 'long' else entry_price * (1 - take_profit_pct)
        
        return trades
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

