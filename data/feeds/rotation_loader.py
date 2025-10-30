"""Rotation universe loader and helpers using local CSV OHLCV files.

Loads multiple symbols' OHLCV data for a given timeframe from data/ohlcv and
provides simple relative-strength utilities for rotation scenarios.
"""
import os
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd


def default_universe() -> List[str]:
    env = os.getenv('ROTATION_UNIVERSE')
    if env:
        return [s.strip() for s in env.split(',') if s.strip()]
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]


def load_rotation_universe(symbols: List[str], timeframe: str, data_dir: str = "data/ohlcv") -> Dict[str, pd.DataFrame]:
    base = Path(data_dir)
    universe: Dict[str, pd.DataFrame] = {}
    for sym in symbols:
        fp = base / f"{sym}_{timeframe}.csv"
        if fp.exists():
            try:
                df = pd.read_csv(fp)
                universe[sym] = df
            except Exception:
                continue
    return universe


def compute_relative_strength(df: pd.DataFrame, ema_span: int = 50) -> pd.Series:
    if df.empty or 'close' not in df:
        return pd.Series(dtype=float)
    ema = df['close'].ewm(span=ema_span, adjust=False).mean()
    rel = (df['close'] / ema) - 1.0
    return rel


def rank_universe_by_strength(universe: Dict[str, pd.DataFrame], ema_span: int = 50) -> List[Tuple[str, float]]:
    scores: List[Tuple[str, float]] = []
    for sym, df in universe.items():
        rel = compute_relative_strength(df, ema_span=ema_span)
        score = float(rel.iloc[-1]) if not rel.empty else float('-inf')
        scores.append((sym, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


