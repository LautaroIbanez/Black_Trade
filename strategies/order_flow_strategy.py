from typing import Dict, Any, List
import pandas as pd
from strategies.strategy_base import StrategyBase


class OrderFlowStrategy(StrategyBase):
    """Heuristic order-flow proxy using volume and price delta.

    Signals when abnormal volume coincides with directional price change.
    """

    def __init__(self, vol_mult: float = 1.8, lookback: int = 30, **kwargs):
        super().__init__(name="OrderFlow", params={"vol_mult": vol_mult, "lookback": lookback}, **kwargs)
        self.vol_mult = vol_mult
        self.lookback = lookback

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        if data.empty:
            data['signal'] = 0
            data['strength'] = 0.0
            return data
        data['ret'] = data['close'].pct_change().fillna(0.0)
        data['vol_ma'] = data['volume'].rolling(self.lookback).mean().fillna(method='bfill')
        data['abnormal_vol'] = (data['volume'] > (self.vol_mult * data['vol_ma'])).astype(int)
        data['signal'] = 0
        data.loc[(data['abnormal_vol'] == 1) & (data['ret'] > 0), 'signal'] = 1
        data.loc[(data['abnormal_vol'] == 1) & (data['ret'] < 0), 'signal'] = -1
        data['strength'] = (data['volume'] / (data['vol_ma'] + 1e-9)).clip(0, 5)
        return data

    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        return []

    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        return self._default_exit_levels(df, signal, entry_price)


