"""
End-to-end test for recommendation service aggregator.
Tests the full pipeline with real fixtures, avoiding dependencies on removed modules.
"""

import pandas as pd
import pytest
from backend.services.recommendation_service import RecommendationService, StrategySignal


def _make_signal(name: str, sig: int, conf: float, score: float, tf: str, price: float = 100.0):
    """Helper to create a StrategySignal with required fields."""
    return StrategySignal(
        strategy_name=name,
        signal=sig,
        strength=conf,
        confidence=conf,
        reason=f"{name} signal",
        price=price,
        timestamp=None,
        score=score,
        timeframe=tf,
        entry_range={"min": price * 0.99, "max": price * 1.01},
        risk_targets={
            "stop_loss": price * 0.98 if sig != -1 else price * 1.02,
            "take_profit": price * 1.04 if sig != -1 else price * 0.96
        },
    )


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    return pd.DataFrame({
        'timestamp': dates,
        'open': 100.0 + (pd.Series(range(100)) * 0.1),
        'high': 101.0 + (pd.Series(range(100)) * 0.1),
        'low': 99.0 + (pd.Series(range(100)) * 0.1),
        'close': 100.0 + (pd.Series(range(100)) * 0.1),
        'volume': 1000.0,
    })


def test_e2e_aggregator_with_real_signals():
    """End-to-end test of aggregator with realistic signal mix."""
    svc = RecommendationService()
    
    # Create a realistic mix of signals across timeframes
    signals = [
        _make_signal("EMA_RSI", 1, 0.7, 0.8, "1h", 50000.0),
        _make_signal("Momentum", 1, 0.6, 0.7, "4h", 50000.0),
        _make_signal("Breakout", -1, 0.5, 0.6, "1d", 50000.0),
        _make_signal("Ichimoku", 0, 0.3, 0.5, "12h", 50000.0),
    ]
    
    # Empty data dict is acceptable for _analyze_signals
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # Assert basic structure
    assert result is not None
    assert result.action in ("BUY", "SELL", "HOLD")
    assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= result.signal_consensus <= 1.0
    assert result.current_price > 0.0
    assert isinstance(result.strategy_details, list)
    assert isinstance(result.entry_range, dict)
    assert "min" in result.entry_range
    assert "max" in result.entry_range
    
    # Assert normalized fields exist
    assert hasattr(result, "risk_reward_ratio")
    assert hasattr(result, "entry_label")
    assert hasattr(result, "risk_percentage")
    assert hasattr(result, "normalized_weights_sum")
    assert hasattr(result, "position_size_usd")
    assert hasattr(result, "position_size_pct")
    
    # Assert normalized fields are in valid ranges
    assert result.risk_reward_ratio >= 0.0
    assert isinstance(result.entry_label, str)
    assert 0.0 <= result.risk_percentage <= 100.0
    assert 0.0 <= result.normalized_weights_sum <= 1.0
    assert result.position_size_usd >= 0.0
    assert 0.0 <= result.position_size_pct <= 1.0


def test_e2e_aggregator_all_buy_signals():
    """Test aggregator with all BUY signals."""
    svc = RecommendationService()
    
    signals = [
        _make_signal("S1", 1, 0.8, 0.9, "1h", 100.0),
        _make_signal("S2", 1, 0.7, 0.8, "4h", 100.0),
        _make_signal("S3", 1, 0.6, 0.7, "1d", 100.0),
    ]
    
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    assert result.action == "BUY"
    assert result.confidence > 0.0
    assert result.signal_consensus > 0.0


def test_e2e_aggregator_all_hold_signals():
    """Test aggregator with all HOLD signals."""
    svc = RecommendationService()
    
    signals = [
        _make_signal("S1", 0, 0.0, 0.5, "1h", 100.0),
        _make_signal("S2", 0, 0.0, 0.5, "4h", 100.0),
    ]
    
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    assert result.action == "HOLD"
    assert result.confidence == 0.0
    assert result.signal_consensus == 0.0


def test_e2e_aggregator_conflicting_signals():
    """Test aggregator with conflicting BUY/SELL signals."""
    svc = RecommendationService()
    
    signals = [
        _make_signal("Buy1", 1, 0.7, 0.8, "1h", 100.0),
        _make_signal("Buy2", 1, 0.6, 0.7, "4h", 100.0),
        _make_signal("Sell1", -1, 0.8, 0.9, "1d", 100.0),
    ]
    
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # Should still produce a valid result (BUY wins by 2-1)
    assert result.action in ("BUY", "SELL", "HOLD")
    assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= result.signal_consensus <= 1.0
    # With 2 BUY vs 1 SELL, should lean BUY
    if result.action == "BUY":
        assert result.signal_consensus > 0.0


def test_e2e_aggregator_mixed_2buy_1sell_1hold_consensus_moderated():
    """Test that 2 BUY / 1 SELL / 1 HOLD scenario keeps consensus moderated (not inflated).
    
    With default mixed_consensus_cap=0.60, consensus should not exceed 0.60 when BUY and SELL coexist.
    """
    svc = RecommendationService()
    
    signals = [
        _make_signal("B1", 1, 0.6, 0.8, "1h", 100.0),
        _make_signal("B2", 1, 0.5, 0.7, "4h", 100.0),
        _make_signal("S1", -1, 0.4, 0.6, "1d", 100.0),
        _make_signal("H1", 0, 0.0, 0.5, "12h", 100.0),
    ]
    
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # Total: 4 signals (2 BUY, 1 SELL, 1 HOLD)
    # Active: 3, Hold: 1
    # Consensus should be moderated by mixed_consensus_cap when BUY/SELL coexist
    
    assert result.action == "BUY"  # BUY should win (2 vs 1)
    assert 0.0 <= result.signal_consensus <= 1.0
    
    # Consensus should be capped at mixed_consensus_cap (default 0.60) when BUY and SELL coexist
    # Without cap: buy_ratio could be ~0.635, but with cap it should be <= 0.60
    assert result.signal_consensus <= 0.60, \
        f"Consensus {result.signal_consensus} should be capped (<= 0.60) in mixed BUY/SELL/HOLD scenario"
    assert result.signal_consensus >= 0.50, \
        f"Consensus {result.signal_consensus} should still show BUY preference (>= 0.50)"


def test_e2e_aggregator_mixed_2buy_1sell_1hold_with_custom_cap():
    """Test that custom mixed_consensus_cap affects consensus moderation.
    
    Lower cap = more conservative consensus in mixed scenarios.
    Higher cap = less moderation (but still capped).
    """
    # More conservative cap
    svc_conservative = RecommendationService(mixed_consensus_cap=0.55)
    # Default cap
    svc_default = RecommendationService(mixed_consensus_cap=0.60)
    # Less conservative cap
    svc_loose = RecommendationService(mixed_consensus_cap=0.65)
    
    signals = [
        _make_signal("B1", 1, 0.6, 0.8, "1h", 100.0),
        _make_signal("B2", 1, 0.5, 0.7, "4h", 100.0),
        _make_signal("S1", -1, 0.4, 0.6, "1d", 100.0),
        _make_signal("H1", 0, 0.0, 0.5, "12h", 100.0),
    ]
    
    result_conservative = svc_conservative._analyze_signals(signals, data={}, profile="balanced")
    result_default = svc_default._analyze_signals(signals, data={}, profile="balanced")
    result_loose = svc_loose._analyze_signals(signals, data={}, profile="balanced")
    
    # Conservative cap should yield lower consensus
    assert result_conservative.signal_consensus <= 0.55, \
        f"Conservative cap should yield consensus <= 0.55. Got: {result_conservative.signal_consensus}"
    assert result_default.signal_consensus <= 0.60, \
        f"Default cap should yield consensus <= 0.60. Got: {result_default.signal_consensus}"
    assert result_loose.signal_consensus <= 0.65, \
        f"Loose cap should yield consensus <= 0.65. Got: {result_loose.signal_consensus}"
    
    # Conservative should be <= default, default should be <= loose
    assert result_conservative.signal_consensus <= result_default.signal_consensus, \
        f"Conservative cap should yield lower/equal consensus. Got: {result_conservative.signal_consensus} vs {result_default.signal_consensus}"
    assert result_default.signal_consensus <= result_loose.signal_consensus, \
        f"Default cap should yield lower/equal consensus than loose. Got: {result_default.signal_consensus} vs {result_loose.signal_consensus}"


def test_e2e_aggregator_mixed_1buy_1sell_multiple_hold():
    """Test 1 BUY / 1 SELL / varios HOLD scenario.
    
    When there are opposing signals (1 BUY, 1 SELL) with multiple HOLD signals,
    consensus should be moderate and reflect the uncertainty.
    """
    svc = RecommendationService()
    
    # Test with 2 HOLD signals
    signals_2hold = [
        _make_signal("B1", 1, 0.6, 0.8, "1h", 100.0),
        _make_signal("S1", -1, 0.5, 0.7, "4h", 100.0),
        _make_signal("H1", 0, 0.0, 0.5, "12h", 100.0),
        _make_signal("H2", 0, 0.0, 0.5, "1d", 100.0),
    ]
    
    result_2hold = svc._analyze_signals(signals_2hold, data={}, profile="balanced")
    
    # Total: 4 signals (1 BUY, 1 SELL, 2 HOLD)
    # Active: 2, Hold: 2
    # With 2 HOLD, neutral_count_threshold=2, so no additional penalty
    # Consensus should be capped at mixed_consensus_cap since BUY and SELL coexist
    assert result_2hold.action in ("BUY", "SELL", "HOLD")  # Either could win
    assert 0.0 <= result_2hold.signal_consensus <= 0.60, \
        f"Consensus {result_2hold.signal_consensus} should be <= 0.60 with opposing signals and HOLD"
    
    # Test with 3 HOLD signals (exceeds threshold)
    signals_3hold = [
        _make_signal("B1", 1, 0.6, 0.8, "1h", 100.0),
        _make_signal("S1", -1, 0.5, 0.7, "4h", 100.0),
        _make_signal("H1", 0, 0.0, 0.5, "12h", 100.0),
        _make_signal("H2", 0, 0.0, 0.5, "1d", 100.0),
        _make_signal("H3", 0, 0.0, 0.5, "1w", 100.0),
    ]
    
    result_3hold = svc._analyze_signals(signals_3hold, data={}, profile="balanced")
    
    # Total: 5 signals (1 BUY, 1 SELL, 3 HOLD)
    # Active: 2, Hold: 3 (exceeds threshold=2, so penalty applies)
    # With 3 HOLD, excess_neutrals = 1, penalty = 0.95^1 = 0.95
    # Consensus should be further reduced by neutral_count_factor
    assert result_3hold.action in ("BUY", "SELL", "HOLD")
    assert 0.0 <= result_3hold.signal_consensus <= 0.60, \
        f"Consensus {result_3hold.signal_consensus} should be <= 0.60 with opposing signals"
    # With neutral penalty, consensus should be lower than without (though calculation is complex)
    assert result_3hold.signal_consensus < 0.70, \
        f"Consensus {result_3hold.signal_consensus} should be moderate with 3+ HOLD signals"


def test_e2e_aggregator_all_hold_consensus_zero():
    """Test that all HOLD signals result in consensus = 0.0 (uncertainty, not conviction)."""
    svc = RecommendationService()
    
    signals = [
        _make_signal("H1", 0, 0.0, 0.5, "1h", 100.0),
        _make_signal("H2", 0, 0.0, 0.5, "4h", 100.0),
        _make_signal("H3", 0, 0.0, 0.5, "1d", 100.0),
        _make_signal("H4", 0, 0.0, 0.5, "12h", 100.0),
    ]
    
    result = svc._analyze_signals(signals, data={}, profile="balanced")
    
    # All HOLD = 100% uncertainty, consensus should be 0.0
    assert result.action == "HOLD"
    assert result.confidence == 0.0, \
        f"Confidence should be 0.0 with all HOLD. Got: {result.confidence}"
    assert result.signal_consensus == 0.0, \
        f"Consensus should be 0.0 with all HOLD (uncertainty). Got: {result.signal_consensus}"


def test_e2e_aggregator_empty_signals():
    """Test aggregator with empty signal list."""
    svc = RecommendationService()
    
    result = svc._analyze_signals([], data={}, profile="balanced")
    
    assert result.action == "HOLD"
    assert result.confidence == 0.0
    assert result.signal_consensus == 0.0
    assert len(result.strategy_details) == 0

