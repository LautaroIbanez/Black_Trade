import pandas as pd
from strategies.macd_crossover_strategy import MACDCrossoverStrategy


def _make_simple_crossover_df() -> pd.DataFrame:
    # Create a synthetic series: uptrend then downtrend to force MACD crossovers
    up = [100 + i * 0.8 for i in range(50)]
    down = [up[-1] - (i + 1) * 0.9 for i in range(50)]
    closes = up + down
    ts = list(range(len(closes)))
    df = pd.DataFrame({
        'timestamp': ts,
        'open': closes,
        'high': [c * 1.002 for c in closes],
        'low': [c * 0.998 for c in closes],
        'close': closes,
        'volume': [100] * len(closes),
    })
    return df


def test_macd_opens_and_closes_with_histogram_zero_cross_and_positive_winrate():
    df = _make_simple_crossover_df()
    # Lower threshold so we don't nullify entries; keep zero_line_cross enabled
    strat = MACDCrossoverStrategy(fast_period=8, slow_period=17, signal_period=6, histogram_threshold=0.0, zero_line_cross=True)
    signals = strat.generate_signals(df)
    trades = strat.generate_trades(signals)
    metrics = strat._calculate_metrics(trades, df)
    assert metrics['total_trades'] > 0
    assert metrics['win_rate'] > 0.0


