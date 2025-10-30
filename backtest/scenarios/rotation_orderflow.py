"""Backtest scenarios for CryptoRotation and OrderFlow strategies."""
from typing import Dict
from strategies.crypto_rotation_strategy import CryptoRotationStrategy
from strategies.order_flow_strategy import OrderFlowStrategy
from data.feeds.rotation_loader import load_rotation_universe


def run_rotation_scenario(symbol: str = "BTCUSDT", timeframe: str = "1h") -> Dict:
    strat = CryptoRotationStrategy(lookback=50)
    universe = load_rotation_universe([symbol], timeframe)
    df = universe.get(symbol)
    if df is None or df.empty:
        return {"error": "No data"}
    return strat.backtest(df)


def run_orderflow_scenario(symbol: str = "BTCUSDT", timeframe: str = "1h") -> Dict:
    strat = OrderFlowStrategy(vol_mult=1.8, lookback=30)
    universe = load_rotation_universe([symbol], timeframe)
    df = universe.get(symbol)
    if df is None or df.empty:
        return {"error": "No data"}
    return strat.backtest(df)


