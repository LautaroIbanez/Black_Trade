"""Backtest scenarios for CryptoRotation and OrderFlow strategies."""
from typing import Dict, List
from strategies.crypto_rotation_strategy import CryptoRotationStrategy
from strategies.order_flow_strategy import OrderFlowStrategy
from data.feeds.rotation_loader import load_rotation_universe, default_universe, rank_universe_by_strength


def run_rotation_scenario(symbols: List[str] = None, timeframe: str = "1h") -> Dict:
    # Choose top symbol by relative strength to simulate rotation selection
    symbols = symbols or default_universe()
    universe = load_rotation_universe(symbols, timeframe)
    if not universe:
        return {"error": "No data"}
    ranked = rank_universe_by_strength(universe, ema_span=50)
    top_sym = ranked[0][0] if ranked else symbols[0]
    df = universe.get(top_sym)
    strat = CryptoRotationStrategy(lookback=50)
    return strat.backtest(df) if df is not None and not df.empty else {"error": "No data"}


def run_orderflow_scenario(symbols: List[str] = None, timeframe: str = "1h") -> Dict:
    symbols = symbols or default_universe()
    universe = load_rotation_universe(symbols, timeframe)
    # Use first available symbol for simple scenario
    for sym in symbols:
        df = universe.get(sym)
        if df is not None and not df.empty:
            strat = OrderFlowStrategy(vol_mult=1.5, lookback=30)
            return strat.backtest(df)
    return {"error": "No data"}


