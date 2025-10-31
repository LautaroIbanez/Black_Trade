"""
Regime detection service using ATR and Keltner Channels.

Classifies market as 'trending' if close breaches Keltner bands, else 'ranging'.
"""
from typing import Dict
import pandas as pd


class RegimeDetector:
    """Detect market regime per timeframe."""

    def __init__(self, ema_period: int = 20, atr_period: int = 14, keltner_mult: float = 1.5):
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.keltner_mult = keltner_mult

    def _atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def detect(self, data_by_tf: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        regimes: Dict[str, str] = {}
        for tf, df in data_by_tf.items():
            if df is None or df.empty:
                regimes[tf] = 'unknown'
                continue
            try:
                close = df['close']
                ema = close.ewm(span=self.ema_period, adjust=False).mean()
                atr = self._atr(df, self.atr_period)
                if atr.empty:
                    regimes[tf] = 'unknown'
                    continue
                upper = ema + self.keltner_mult * atr
                lower = ema - self.keltner_mult * atr
                last_close = float(close.iloc[-1])
                last_upper = float(upper.iloc[-1])
                last_lower = float(lower.iloc[-1])
                if last_close > last_upper or last_close < last_lower:
                    regimes[tf] = 'trending'
                else:
                    regimes[tf] = 'ranging'
            except Exception:
                regimes[tf] = 'unknown'
        return regimes


# Global instance
regime_detector = RegimeDetector()




