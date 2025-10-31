"""Rotation universe loader and helpers using local CSV OHLCV files.

Loads multiple symbols' OHLCV data for a given timeframe from data/ohlcv and
provides simple relative-strength utilities for rotation scenarios with
timestamp alignment and normalization.
"""
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np


def default_universe() -> List[str]:
    """Get default rotation universe from env or default list."""
    env = os.getenv('ROTATION_UNIVERSE')
    if env:
        return [s.strip() for s in env.split(',') if s.strip()]
    return ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]


def load_rotation_universe(symbols: List[str], timeframe: str, data_dir: str = "data/ohlcv") -> Dict[str, pd.DataFrame]:
    """Load OHLCV data for multiple symbols from CSV files.
    
    Args:
        symbols: List of symbol names to load
        timeframe: Timeframe string (e.g., '1h', '4h', '1d')
        data_dir: Base directory for OHLCV CSV files
        
    Returns:
        Dictionary mapping symbol names to DataFrames with OHLCV data
    """
    base = Path(data_dir)
    universe: Dict[str, pd.DataFrame] = {}
    for sym in symbols:
        fp = base / f"{sym}_{timeframe}.csv"
        if fp.exists():
            try:
                df = pd.read_csv(fp)
                # Ensure timestamp column exists and is datetime
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp').reset_index(drop=True)
                universe[sym] = df
            except Exception as e:
                print(f"Warning: Failed to load {sym} from {fp}: {e}")
                continue
    return universe


def align_universe_timestamps(universe: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Align timestamps across all symbols in universe.
    
    Creates a common timestamp index by finding the intersection of all
    timestamps, ensuring all symbols have data at the same timestamps.
    
    Args:
        universe: Dictionary of symbol -> DataFrame with 'timestamp' column
        
    Returns:
        Dictionary with aligned DataFrames (may have NaN where data is missing)
    """
    if not universe:
        return {}
    
    # Find common timestamps (intersection)
    all_timestamps = None
    for sym, df in universe.items():
        if df is not None and not df.empty and 'timestamp' in df.columns:
            ts = pd.to_datetime(df['timestamp']).drop_duplicates().sort_values()
            if all_timestamps is None:
                all_timestamps = ts
            else:
                all_timestamps = all_timestamps[all_timestamps.isin(ts)]
    
    if all_timestamps is None or len(all_timestamps) == 0:
        return universe
    
    # Reindex all dataframes to common timestamps
    aligned = {}
    for sym, df in universe.items():
        if df is not None and not df.empty and 'timestamp' in df.columns:
            df_copy = df.copy()
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
            df_copy = df_copy.set_index('timestamp')
            df_aligned = df_copy.reindex(all_timestamps)
            df_aligned = df_aligned.reset_index()
            aligned[sym] = df_aligned
        else:
            aligned[sym] = df
    
    return aligned


def compute_relative_strength(df: pd.DataFrame, ema_span: int = 50) -> pd.Series:
    """Compute relative strength as (close/EMA - 1).
    
    Args:
        df: DataFrame with 'close' column
        ema_span: Period for EMA calculation
        
    Returns:
        Series with relative strength values
    """
    if df is None or df.empty or 'close' not in df.columns:
        return pd.Series(dtype=float)
    close = df['close'].dropna()
    if close.empty:
        return pd.Series(dtype=float)
    ema = close.ewm(span=ema_span, adjust=False).mean()
    rel = (close / ema) - 1.0
    return rel.fillna(0.0)


def compute_returns(df: pd.DataFrame, periods: int = 1) -> pd.Series:
    """Compute returns over specified periods.
    
    Args:
        df: DataFrame with 'close' column
        periods: Number of periods for return calculation
        
    Returns:
        Series with return values (pct_change)
    """
    if df is None or df.empty or 'close' not in df.columns:
        return pd.Series(dtype=float)
    close = df['close'].dropna()
    if close.empty or len(close) <= periods:
        return pd.Series(dtype=float)
    return close.pct_change(periods=periods).fillna(0.0)


def compute_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Compute rolling volatility (std of returns).
    
    Args:
        df: DataFrame with 'close' column
        window: Rolling window size
        
    Returns:
        Series with volatility values
    """
    if df is None or df.empty or 'close' not in df.columns:
        return pd.Series(dtype=float)
    returns = compute_returns(df, periods=1)
    if returns.empty or len(returns) < window:
        return pd.Series(dtype=float)
    return returns.rolling(window=window).std().fillna(0.0)


def rank_universe_by_strength(universe: Dict[str, pd.DataFrame], ema_span: int = 50) -> List[Tuple[str, float]]:
    """Rank symbols by relative strength (latest value).
    
    Args:
        universe: Dictionary of symbol -> DataFrame
        ema_span: Period for EMA calculation
        
    Returns:
        List of (symbol, score) tuples sorted by score (descending)
    """
    scores: List[Tuple[str, float]] = []
    for sym, df in universe.items():
        if df is None or df.empty:
            scores.append((sym, float('-inf')))
            continue
        rel = compute_relative_strength(df, ema_span=ema_span)
        score = float(rel.iloc[-1]) if not rel.empty else float('-inf')
        scores.append((sym, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def rank_universe_by_returns(universe: Dict[str, pd.DataFrame], periods: int = 20) -> List[Tuple[str, float]]:
    """Rank symbols by returns over specified periods.
    
    Args:
        universe: Dictionary of symbol -> DataFrame
        periods: Number of periods for return calculation
        
    Returns:
        List of (symbol, return) tuples sorted by return (descending)
    """
    scores: List[Tuple[str, float]] = []
    for sym, df in universe.items():
        if df is None or df.empty:
            scores.append((sym, float('-inf')))
            continue
        returns = compute_returns(df, periods=periods)
        score = float(returns.iloc[-1]) if not returns.empty else float('-inf')
        scores.append((sym, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def rank_universe_by_sharpe(universe: Dict[str, pd.DataFrame], window: int = 20, risk_free: float = 0.0) -> List[Tuple[str, float]]:
    """Rank symbols by Sharpe ratio (return / volatility).
    
    Args:
        universe: Dictionary of symbol -> DataFrame
        window: Rolling window for volatility calculation
        risk_free: Risk-free rate (default 0)
        
    Returns:
        List of (symbol, sharpe_ratio) tuples sorted by ratio (descending)
    """
    scores: List[Tuple[str, float]] = []
    for sym, df in universe.items():
        if df is None or df.empty:
            scores.append((sym, float('-inf')))
            continue
        returns = compute_returns(df, periods=1)
        volatility = compute_volatility(df, window=window)
        
        if returns.empty or volatility.empty:
            scores.append((sym, float('-inf')))
            continue
        
        # Annualized Sharpe (assuming daily data)
        mean_return = returns.iloc[-window:].mean() if len(returns) >= window else returns.mean()
        vol = volatility.iloc[-1] if not volatility.empty else 0.0
        
        if vol > 0:
            sharpe = (mean_return - risk_free) / vol
            scores.append((sym, float(sharpe)))
        else:
            scores.append((sym, float('-inf')))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


