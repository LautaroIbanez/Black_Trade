"""Simple rotation universe loader using local CSV OHLCV files.

Loads multiple symbols' OHLCV data for a given timeframe from data/ohlcv.
"""
import os
from pathlib import Path
from typing import Dict, List
import pandas as pd


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


