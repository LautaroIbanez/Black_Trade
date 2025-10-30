import math

from backend.services.recommendation_service import RecommendationService, StrategySignal


def _mk_signal(name: str, sig: int, conf: float, strg: float, score: float, tf: str, price: float = 100.0):
    return StrategySignal(
        strategy_name=name,
        signal=sig,
        strength=strg,
        confidence=conf,
        reason="test",
        price=price,
        timestamp=None,
        score=score,
        timeframe=tf,
        entry_range={"min": price * 0.99, "max": price * 1.01},
        risk_targets={"stop_loss": price * 0.98 if sig != -1 else price * 1.02,
                      "take_profit": price * 1.04 if sig != -1 else price * 0.96},
    )


def test_confidence_floor_does_not_exceed_weakest_supporting_signal():
    svc = RecommendationService()
    # Two BUY primaries: weakest confidence deliberately below prior floor (0.30)
    weakest_conf = 0.12
    signals = [
        _mk_signal("S1", 1, weakest_conf, 0.5, 0.9, "1d"),
        _mk_signal("S2", 1, 0.80, 0.7, 0.8, "4h"),
        # Some neutrals that shouldn't dominate
        _mk_signal("S3", 0, 0.20, 0.3, 0.6, "1h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    assert result.action in ("BUY", "SELL", "HOLD")
    # Integrity: confidence must not be forced above weakest supporting confidence
    assert result.confidence <= weakest_conf + 1e-9
    assert 0.0 <= result.confidence <= 1.0


def test_signal_consensus_is_capped_to_one():
    svc = RecommendationService()
    # Many BUY signals to push raw consensus above 1.0 when boosted
    signals = [
        _mk_signal(f"SB{i}", 1, 0.5, 0.5, 0.5, "4h") for i in range(5)
    ] + [
        _mk_signal("SH", 0, 0.2, 0.2, 0.5, "1d")
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    assert 0.0 <= result.signal_consensus <= 1.0
    # With clear BUY majority, action should not be HOLD
    assert result.action != "HOLD"


def test_single_weak_signal_confidence_low_and_no_floor_push():
    svc = RecommendationService()
    weakest_conf = 0.08
    signals = [
        _mk_signal("S1", 1, weakest_conf, 0.2, 0.5, "1h"),
        _mk_signal("N1", 0, 0.0, 0.0, 0.5, "4h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    assert 0.0 <= result.confidence <= weakest_conf + 1e-9


def test_conflicting_signals_consensus_within_bounds():
    svc = RecommendationService()
    signals = [
        _mk_signal("B1", 1, 0.3, 0.3, 0.5, "1h"),
        _mk_signal("S1", -1, 0.3, 0.3, 0.5, "1h"),
        _mk_signal("H1", 0, 0.2, 0.2, 0.5, "4h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    assert 0.0 <= result.signal_consensus <= 1.0

def test_position_sizing_consolidated_fields_present_and_consistent():
    svc = RecommendationService()
    price = 100.0
    sl = 98.0
    signals = [
        _mk_signal("S1", 1, 0.6, 0.7, 0.6, "1h", price),
        _mk_signal("S2", 1, 0.5, 0.6, 0.5, "4h", price),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    # Fields exist and are non-negative
    assert hasattr(result, "position_size_usd") and hasattr(result, "position_size_pct")
    assert result.position_size_usd >= 0.0
    assert 0.0 <= result.position_size_pct <= 1.0


def test_includes_new_timeframes_in_aggregation_when_present():
    svc = RecommendationService()
    signals = [
        _mk_signal("S15m", 1, 0.4, 0.5, 0.6, "15m"),
        _mk_signal("S2h", 1, 0.5, 0.6, 0.6, "2h"),
        _mk_signal("S12h", -1, 0.6, 0.4, 0.6, "12h"),
        _mk_signal("S1d", 0, 0.3, 0.3, 0.5, "1d"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    # Ensure strategy_details reflect all provided timeframes
    timeframes_in_result = {d.get("timeframe") for d in result.strategy_details}
    assert {"15m", "2h", "12h"}.issubset(timeframes_in_result)


