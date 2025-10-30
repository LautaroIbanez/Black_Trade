from backend.services.risk_management import RiskManagementService


def test_dynamic_buffer_low_volatility():
    svc = RiskManagementService()
    current_price = 100.0
    entry_range = {"min": 99.0, "max": 101.0}
    # Very low ATR -> small buffer
    atr_value = 0.2  # 0.2 absolute price units
    # Long position scenario: SL initially too close
    sl = 98.9
    tp = 102.0
    adj_sl, adj_tp = svc._ensure_levels_outside_entry_range(sl, tp, entry_range, current_price, atr_value=atr_value, profile="balanced")
    # Balanced profile entry_buffer_atr_mult=0.7 => buffer=0.14
    expected_buffer = atr_value * 0.7
    assert abs((entry_range['min'] - expected_buffer) - adj_sl) < 1e-6
    assert adj_tp >= entry_range['max'] + expected_buffer


def test_dynamic_buffer_high_volatility():
    svc = RiskManagementService()
    current_price = 100.0
    entry_range = {"min": 95.0, "max": 105.0}
    # High ATR -> larger buffer
    atr_value = 5.0
    sl = 96.0
    tp = 104.0
    adj_sl, adj_tp = svc._ensure_levels_outside_entry_range(sl, tp, entry_range, current_price, atr_value=atr_value, profile="swing")
    # Swing profile entry_buffer_atr_mult=0.8 => buffer=4.0
    expected_buffer = atr_value * 0.8
    assert adj_sl <= entry_range['min'] - expected_buffer + 1e-9
    assert adj_tp >= entry_range['max'] + expected_buffer - 1e-9


