from typing import Dict, Any, List
import pandas as pd
from strategies.strategy_base import StrategyBase


class CryptoRotationStrategy(StrategyBase):
    """Simple single-symbol proxy for rotation based on recent relative strength vs. EMA.

    Note: In a single-symbol context, this approximates rotation by favoring momentum
    when price is above EMA and penalizing when below.
    """

    def __init__(self, lookback: int = 50, **kwargs):
        super().__init__(name="CryptoRotation", params={"lookback": lookback}, **kwargs)
        self.lookback = lookback

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        if data.empty:
            data['signal'] = 0
            data['strength'] = 0.0
            return data
        data['ema'] = data['close'].ewm(span=self.lookback, adjust=False).mean()
        data['rel'] = (data['close'] / data['ema']) - 1.0
        data['strength'] = data['rel'].rolling(5).mean().fillna(0.0).clip(-1, 1)
        data['signal'] = 0
        data.loc[data['rel'] > 0.005, 'signal'] = 1
        data.loc[data['rel'] < -0.005, 'signal'] = -1
        return data

    def generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        return []

    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        # Use default fallback in base class via risk_targets pathway
        return self._default_exit_levels(df, signal, entry_price)


