import os
import pytest

from backend.scripts.init_risk_system import init_risk_system


@pytest.fixture(scope="module")
def risk_engine():
    # Force simulated env
    os.environ['USE_SIMULATED_RISK'] = 'true'
    engine, adapter = init_risk_system(use_simulated=True)
    return engine


def test_var_and_drawdown_calculation(risk_engine):
    # Ensure metrics can be computed without errors
    var = risk_engine.calculate_var()
    assert 'var_1d_95' in var and 'var_1w_95' in var
    assert var['var_1d_95'] >= 0

    dd = risk_engine.calculate_drawdown()
    assert 'current_drawdown_pct' in dd and 'max_drawdown_pct' in dd
    assert dd['current_drawdown_pct'] >= 0


def test_get_risk_metrics_has_core_fields(risk_engine):
    metrics = risk_engine.get_risk_metrics()
    assert metrics.total_capital is not None
    assert metrics.total_exposure is not None
    assert metrics.exposure_pct is not None
    assert metrics.var_1d_95 is not None
    assert metrics.current_drawdown_pct is not None

