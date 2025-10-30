"""Analysis utilities for ranking strategies without hard caps.

Combines return, relative drawdown, and trade count into a composite score.
Eliminates previous hard clamping (e.g., min(..., 1.0)) to preserve comparability.
"""
from typing import Dict, Any


def compute_composite_score(result: Dict[str, Any]) -> float:
    """Compute a composite score from backtest metrics.

    Components:
    - Risk-adjusted return: total_return_pct - max_drawdown_pct
    - Stability: profit_factor relative to 1.0 and win_rate support
    - Activity: trade count scaling (diminishing beyond ~50 trades)
    - Expectancy: scaled contribution per trade

    Strategies with zero trades are heavily penalized.
    """
    total_return = float(result.get('total_return_pct', 0.0) or 0.0)
    max_dd = float(result.get('max_drawdown_pct', 0.0) or 0.0)
    profit_factor = float(result.get('profit_factor', 0.0) or 0.0)
    win_rate = float(result.get('win_rate', 0.0) or 0.0)
    expectancy = float(result.get('expectancy', 0.0) or 0.0)
    trades = int(result.get('total_trades', len(result.get('trades', []) or [])) or 0)

    if trades <= 0:
        # Strong penalty for inactive strategies
        return -1.0

    # Risk-adjusted return favors high return and lower drawdown
    risk_adjusted_return = total_return - max_dd

    # Stability: center profit factor around 1.0; include win rate support
    stability = (profit_factor - 1.0) + (win_rate - 0.5)

    # Activity scaling: diminishes beyond 50 trades
    activity_scale = min(trades / 50.0, 1.0)

    # Expectancy is typically in absolute currency; scale to a modest contribution
    expectancy_scaled = expectancy / 100.0

    # Combine with weights; no hard clamping applied
    composite = (risk_adjusted_return * 0.6) + (stability * 0.25) + (expectancy_scaled * 0.15)
    score = composite * (0.5 + 0.5 * activity_scale)
    return float(score)


