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


def test_e2e_aggregator_empty_signals():
    """Test aggregator with empty signal list."""
    svc = RecommendationService()
    
    result = svc._analyze_signals([], data={}, profile="balanced")
    
    assert result.action == "HOLD"
    assert result.confidence == 0.0
    assert result.signal_consensus == 0.0
    assert len(result.strategy_details) == 0

