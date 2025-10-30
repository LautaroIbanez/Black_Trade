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
        trades: List[Dict] = []
        if df.empty or 'signal' not in df.columns:
            return trades
        position = None
        for idx in range(len(df)):
            row = df.iloc[idx]
            ts = row.get('timestamp')
            price = float(row.get('close', 0))
            sig = int(row.get('signal', 0))
            # Entry conditions
            if position is None:
                if sig == 1:
                    position = {"side": "long", "entry_price": price, "entry_time": ts}
                elif sig == -1:
                    position = {"side": "short", "entry_price": price, "entry_time": ts}
                continue
            # Exit on opposite signal
            if position and ((position['side'] == 'long' and sig == -1) or (position['side'] == 'short' and sig == 1)):
                exit_price = price
                pnl = (exit_price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - exit_price)
                trade = {
                    "entry_price": position['entry_price'],
                    "exit_price": exit_price,
                    "side": position['side'],
                    "pnl": pnl,
                    "entry_time": position['entry_time'],
                    "exit_time": ts
                }
                trades.append(trade)
                position = None
        # Close any open position at last price
        if position is not None and not df.empty:
            last = df.iloc[-1]
            exit_price = float(last.get('close', 0))
            pnl = (exit_price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - exit_price)
            trade = {
                "entry_price": position['entry_price'],
                "exit_price": exit_price,
                "side": position['side'],
                "pnl": pnl,
                "entry_time": position['entry_time'],
                "exit_time": last.get('timestamp'),
                "forced_close": True
            }
            trades.append(trade)
        return trades

    def calculate_exit_levels(self, df: pd.DataFrame, signal: int, entry_price: float) -> Dict[str, float]:
        # Use default fallback in base class via risk_targets pathway
        return self._default_exit_levels(df, signal, entry_price)



