from backend.services.recommendation_service import RecommendationService, StrategySignal


def _make_signal(name: str, sig: int, conf: float, score: float, tf: str) -> StrategySignal:
    return StrategySignal(
        strategy_name=name,
        signal=sig,
        strength=conf,
        confidence=conf,
        reason="",
        price=100.0,
        timestamp=0,
        score=score,
        timeframe=tf,
        entry_range={"min": 99.0, "max": 101.0},
        risk_targets={"stop_loss": 98.0, "take_profit": 102.0},
    )


def test_confidence_capped_by_min_active_and_mean():
    svc = RecommendationService()
    # Highly unbalanced: one weak active (0.12), others strong (0.8)
    signals = [
        _make_signal("Strong1", 1, 0.8, 1.0, "1h"),
        _make_signal("Strong2", 1, 0.8, 1.0, "4h"),
        _make_signal("Weak", 1, 0.12, 1.0, "1d"),
        _make_signal("Neutral", 0, 0.3, 1.0, "12h"),
    ]
    res = svc._analyze_signals(signals, data={}, profile="balanced")
    active = [s for s in signals if s.signal != 0]
    active_conf = [min(max(s.confidence * s.score, 0.0), 1.0) for s in active]
    mean_active = sum(active_conf) / len(active_conf)
    min_active = min(active_conf)
    assert 0.0 <= res.confidence <= 1.0
    assert res.confidence <= mean_active
    assert res.confidence <= min_active


def test_consensus_within_bounds_and_no_inflation():
    svc = RecommendationService()
    # Two buys, one sell, one hold -> majority 2/4
    signals = [
        _make_signal("S1", 1, 0.3, 0.8, "1h"),
        _make_signal("S2", 1, 0.2, 0.7, "4h"),
        _make_signal("S3", -1, 0.6, 0.9, "1d"),
        _make_signal("S4", 0, 0.5, 0.5, "12h"),
    ]
    res = svc._analyze_signals(signals, data={}, profile="balanced")
    assert 0.0 <= res.signal_consensus <= 1.0


def test_consensus_mixed_signals_2buy_1sell_3hold():
    """Consensus with 2 BUY / 1 SELL / 3 HOLD should not inflate due to neutrals being marginalized."""
    svc = RecommendationService()
    signals = [
        _make_signal("B1", 1, 0.4, 0.8, "1h"),
        _make_signal("B2", 1, 0.5, 0.7, "4h"),
        _make_signal("S1", -1, 0.6, 0.9, "1d"),
        _make_signal("H1", 0, 0.3, 0.5, "12h"),
        _make_signal("H2", 0, 0.2, 0.4, "15m"),
        _make_signal("H3", 0, 0.25, 0.5, "2h"),
    ]
    res = svc._analyze_signals(signals, data={}, profile="balanced")
    # With dynamic neutral weighting, consensus should be more conservative
    # Neutrals (3/6 = 50%) get at least 0.3 * 0.5 = 15% weight floor
    # Effective total: 3 active + (3 * max(0.15, min(0.5, 0.15))) = 3 + 0.45 = 3.45
    # Buy ratio: 2 / 3.45 ≈ 0.58, not inflated to ~0.65
    assert 0.0 <= res.signal_consensus <= 1.0
    # Consensus should not exceed what we'd get with simple majority among actives
    # Simple majority: 2/3 ≈ 0.67, but with weighted neutrals it should be lower
    assert res.signal_consensus <= 0.70  # Allow some tolerance
    # Should still favor BUY but not overconfidently
    assert res.action == "BUY"


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


def test_all_hold_reflects_uncertainty_zero_consensus():
    """Test that 100% HOLD scenarios result in consensus = 0 (uncertainty), not 1.0 (conviction)."""
    svc = RecommendationService()
    # All signals are HOLD
    signals = [
        _mk_signal("H1", 0, 0.0, 0.0, 0.5, "1h"),
        _mk_signal("H2", 0, 0.0, 0.0, 0.5, "4h"),
        _mk_signal("H3", 0, 0.0, 0.0, 0.5, "1d"),
        _mk_signal("H4", 0, 0.0, 0.0, 0.5, "12h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # 100% HOLD = uncertainty, consensus should be 0.0 (or very low configurable threshold)
    assert result.signal_consensus == 0.0, f"Expected 0.0 for all HOLD, got {result.signal_consensus}"
    assert result.action == "HOLD"
    assert result.confidence == 0.0  # No active signals means no confidence


def test_mixed_signals_2buy_1sell_rest_hold_consensus_within_weighted_average():
    """Test that 2 BUY / 1 SELL / 4 HOLD scenario keeps consensus within weighted average."""
    svc = RecommendationService()
    signals = [
        _mk_signal("B1", 1, 0.6, 0.7, 0.8, "1h"),
        _mk_signal("B2", 1, 0.5, 0.6, 0.7, "4h"),
        _mk_signal("S1", -1, 0.4, 0.5, 0.6, "1d"),
        _mk_signal("H1", 0, 0.0, 0.0, 0.5, "12h"),
        _mk_signal("H2", 0, 0.0, 0.0, 0.5, "15m"),
        _mk_signal("H3", 0, 0.0, 0.0, 0.5, "2h"),
        _mk_signal("H4", 0, 0.0, 0.0, 0.5, "4h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # Total: 7 signals (2 BUY, 1 SELL, 4 HOLD)
    # Active: 3, Hold: 4
    # Neutrals should have residual weight, consensus should reflect uncertainty
    
    # Calculate weighted average of active signals
    active_signals = [s for s in signals if s.signal != 0]
    active_confidences = [min(max(s.confidence * s.score, 0.0), 1.0) for s in active_signals]
    weighted_avg = sum(active_confidences) / len(active_confidences) if active_confidences else 0.0
    
    # Consensus should be within bounds and reflect that neutrals dominate
    assert 0.0 <= result.signal_consensus <= 1.0
    
    # Since neutrals (4) > active (3), consensus should be capped/scaled down
    # It should never reach 1.0 when neutrals dominate
    assert result.signal_consensus < 1.0, "Consensus should not reach 1.0 when neutrals dominate"
    
    # Consensus should be less than or equal to weighted average (conservative)
    # Allow some tolerance for the scaling logic
    assert result.signal_consensus <= weighted_avg + 0.1, \
        f"Consensus {result.signal_consensus} should not exceed weighted avg {weighted_avg} significantly"
    
    # Since BUY > SELL, action should be BUY
    assert result.action == "BUY"


def test_consensus_never_reaches_one_when_neutrals_predominate():
    """Test that consensus never reaches 1.0 when hold signals outnumber active signals."""
    svc = RecommendationService()
    
    # Scenario: 1 BUY, 5 HOLD (neutrals predominate 5:1)
    signals = [
        _mk_signal("B1", 1, 0.9, 0.9, 1.0, "1h"),  # Very strong BUY
        _mk_signal("H1", 0, 0.0, 0.0, 0.5, "4h"),
        _mk_signal("H2", 0, 0.0, 0.0, 0.5, "1d"),
        _mk_signal("H3", 0, 0.0, 0.0, 0.5, "12h"),
        _mk_signal("H4", 0, 0.0, 0.0, 0.5, "15m"),
        _mk_signal("H5", 0, 0.0, 0.0, 0.5, "2h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # Even with a strong BUY signal, consensus should be capped when neutrals dominate
    assert result.signal_consensus < 1.0, \
        f"Consensus {result.signal_consensus} should never reach 1.0 when neutrals (5) > active (1)"
    
    # With 1 active out of 6 total (16.7%), max consensus should be scaled accordingly
    # Active proportion = 1/6 ≈ 0.167
    # Expected cap: some function of active proportion, definitely < 0.5
    max_expected = 0.5 * (1 / 6) + 0.3  # From the formula in code
    assert result.signal_consensus <= max_expected + 0.1, \
        f"Consensus {result.signal_consensus} should be capped by active proportion"


def test_mixed_signals_with_equal_buy_sell_and_many_hold():
    """Test consensus when BUY and SELL are equal but many HOLD signals exist."""
    svc = RecommendationService()
    signals = [
        _mk_signal("B1", 1, 0.7, 0.8, 0.9, "1h"),
        _mk_signal("S1", -1, 0.7, 0.8, 0.9, "4h"),
        _mk_signal("H1", 0, 0.0, 0.0, 0.5, "1d"),
        _mk_signal("H2", 0, 0.0, 0.0, 0.5, "12h"),
        _mk_signal("H3", 0, 0.0, 0.0, 0.5, "15m"),
        _mk_signal("H4", 0, 0.0, 0.0, 0.5, "2h"),
    ]
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # 2 active (1 BUY, 1 SELL), 4 HOLD
    # Consensus should reflect the conflict (equal BUY/SELL) and uncertainty (many HOLD)
    assert 0.0 <= result.signal_consensus <= 1.0
    
    # With equal BUY/SELL, consensus should be low (no clear direction)
    # And with many HOLD (4 > 2 active), should be further reduced
    assert result.signal_consensus < 0.6, \
        f"Consensus {result.signal_consensus} should be low with equal BUY/SELL and many HOLD"
    
    # Action should likely be HOLD due to conflict and uncertainty
    # But could be either BUY or SELL if one slightly wins
    assert result.action in ("BUY", "SELL", "HOLD")


