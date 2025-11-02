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


def load_rotation_universe(symbols: List[str], timeframe: str, data_dir: str = "data/ohlcv", 
                          min_required: Optional[int] = None, strict: bool = False) -> Dict[str, pd.DataFrame]:
    """Load OHLCV data for multiple symbols from CSV files.
    
    Args:
        symbols: List of symbol names to load
        timeframe: Timeframe string (e.g., '1h', '4h', '1d')
        data_dir: Base directory for OHLCV CSV files
        min_required: Minimum number of symbols required (None = all symbols)
        strict: If True, raise ValueError when symbols are missing. If False, warn and continue.
        
    Returns:
        Dictionary mapping symbol names to DataFrames with OHLCV data
        
    Raises:
        ValueError: If strict=True and any required symbol is missing
        RuntimeError: If strict=False but less than min_required symbols are loaded
    """
    base = Path(data_dir)
    universe: Dict[str, pd.DataFrame] = {}
    missing_symbols: List[str] = []
    failed_symbols: List[Tuple[str, str]] = []  # (symbol, error_message)
    
    for sym in symbols:
        fp = base / f"{sym}_{timeframe}.csv"
        if not fp.exists():
            missing_symbols.append(sym)
            if strict:
                raise ValueError(f"Required symbol data missing: {sym} at {fp}")
            continue
        
        try:
            df = pd.read_csv(fp)
            
            # Validate required columns
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                error_msg = f"Missing required columns: {missing_cols}"
                failed_symbols.append((sym, error_msg))
                if strict:
                    raise ValueError(f"Invalid data for {sym}: {error_msg}")
                continue
            
            # Ensure timestamp column exists and is datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Validate data is not empty
            if df.empty:
                failed_symbols.append((sym, "DataFrame is empty after loading"))
                if strict:
                    raise ValueError(f"Empty data for {sym}: {fp}")
                continue
            
            # Validate minimum data points (at least lookback periods needed)
            if len(df) < 50:  # Minimum for typical EMA calculations
                failed_symbols.append((sym, f"Insufficient data points: {len(df)} < 50"))
                # Don't fail strict mode for this, but warn
            
            universe[sym] = df
            
        except Exception as e:
            error_msg = str(e)
            failed_symbols.append((sym, error_msg))
            if strict:
                raise ValueError(f"Failed to load {sym} from {fp}: {error_msg}")
            continue
    
    # Log warnings/errors for missing/failed symbols
    if missing_symbols or failed_symbols:
        import logging
        logger = logging.getLogger(__name__)
        if missing_symbols:
            error_msg = f"ALERT: Missing symbols ({len(missing_symbols)}/{len(symbols)}): {missing_symbols}. Rotation may degrade to fallback mode."
            if strict:
                logger.error(error_msg)
            else:
                logger.warning(error_msg)
        if failed_symbols:
            error_msg = f"ALERT: Failed to load symbols ({len(failed_symbols)}/{len(symbols)}): {[s[0] for s in failed_symbols]}"
            if strict:
                logger.error(error_msg)
            else:
                logger.warning(error_msg)
            for sym, error in failed_symbols:
                detail_msg = f"  {sym}: {error}"
                if strict:
                    logger.error(detail_msg)
                else:
                    logger.warning(detail_msg)
    
    # Validate minimum required symbols
    loaded_count = len(universe)
    if min_required is not None and loaded_count < min_required:
        error_msg = f"Insufficient symbols loaded: {loaded_count} < {min_required} required"
        if strict:
            raise RuntimeError(error_msg)
        else:
            import logging
            logging.getLogger(__name__).error(error_msg)
    
    # Ensure at least 2 symbols for rotation (single symbol = no rotation)
    if loaded_count < 2:
        error_msg = f"ALERT: Rotation requires at least 2 symbols, but only {loaded_count} loaded. Missing: {missing_symbols}. Strategy will degrade to single-asset fallback mode."
        if strict:
            import logging
            logging.getLogger(__name__).error(error_msg)
            raise RuntimeError(error_msg)
        else:
            import logging
            logging.getLogger(__name__).warning(error_msg)
    
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


