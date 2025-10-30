from backtest.engine.analysis import compute_composite_score


def test_zero_trades_heavily_penalized():
    res = {
        'total_return_pct': 0.2,
        'max_drawdown_pct': 0.05,
        'profit_factor': 1.5,
        'win_rate': 0.6,
        'expectancy': 10.0,
        'total_trades': 0,
    }
    score = compute_composite_score(res)
    assert score < 0.0


def test_risk_adjusted_combination_without_hard_cap():
    high = {
        'total_return_pct': 1.5,  # 150%
        'max_drawdown_pct': 0.2,
        'profit_factor': 2.5,
        'win_rate': 0.7,
        'expectancy': 50.0,
        'total_trades': 60,
    }
    moderate = {
        'total_return_pct': 0.4,
        'max_drawdown_pct': 0.1,
        'profit_factor': 1.6,
        'win_rate': 0.6,
        'expectancy': 15.0,
        'total_trades': 25,
    }
    s_high = compute_composite_score(high)
    s_mod = compute_composite_score(moderate)
    # No universal cap at 1.0 should force equality
    assert s_high > s_mod


