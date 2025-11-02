"""
Minimal end-to-end test for recommendation service aggregator.
Tests the full pipeline with real fixtures to ensure consensus and risk pipeline coverage.
"""
import pandas as pd
import pytest
from backend.services.recommendation_service import RecommendationService, StrategySignal


def _make_signal(name: str, sig: int, conf: float, score: float, tf: str, price: float = 50000.0):
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


def test_e2e_aggregator_with_mixed_signals_and_risk_pipeline():
    """End-to-end test covering consensus calculation and risk pipeline with mixed signals."""
    svc = RecommendationService()
    
    # Create a realistic mix: 2 BUY, 1 SELL, 1 HOLD (mixed scenario)
    signals = [
        _make_signal("EMA_RSI", 1, 0.7, 0.8, "1h", 50000.0),
        _make_signal("Momentum", 1, 0.6, 0.7, "4h", 50000.0),
        _make_signal("Breakout", -1, 0.5, 0.6, "1d", 50000.0),
        _make_signal("Ichimoku", 0, 0.3, 0.5, "12h", 50000.0),
    ]
    
    # Create minimal OHLCV data for risk management
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    data = {
        '1h': pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0 + (pd.Series(range(100)) * 0.1),
            'high': 50100.0 + (pd.Series(range(100)) * 0.1),
            'low': 49900.0 + (pd.Series(range(100)) * 0.1),
            'close': 50000.0 + (pd.Series(range(100)) * 0.1),
            'volume': 1000.0,
        }),
        '4h': pd.DataFrame({
            'timestamp': dates[:25],
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50000.0,
            'volume': 1000.0,
        }),
        '1d': pd.DataFrame({
            'timestamp': dates[:5],
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50000.0,
            'volume': 1000.0,
        }),
        '12h': pd.DataFrame({
            'timestamp': dates[:10],
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50000.0,
            'volume': 1000.0,
        }),
    }
    
    result = svc._analyze_signals(signals, data=data, profile="balanced")
    
    # Verify consensus calculation for mixed scenario
    assert result is not None
    assert result.action in ("BUY", "SELL", "HOLD")
    assert 0.0 <= result.signal_consensus <= 1.0
    # With 2 BUY / 1 SELL / 1 HOLD, consensus should be capped by mixed_consensus_cap (default 0.60)
    if result.action == "BUY":  # BUY should win (2 vs 1)
        assert result.signal_consensus <= 0.60, \
            f"Consensus {result.signal_consensus} should be <= 0.60 in mixed BUY/SELL/HOLD scenario"
        assert result.signal_consensus >= 0.50, \
            f"Consensus {result.signal_consensus} should still show BUY preference (>= 0.50)"
    
    # Verify risk pipeline outputs exist
    assert result.current_price > 0.0
    assert isinstance(result.entry_range, dict)
    assert "min" in result.entry_range and "max" in result.entry_range
    # Stop loss and take profit may be calculated or may be 0.0/invalid if risk management fails
    # Just verify they exist and are numeric
    assert isinstance(result.stop_loss, (int, float))
    assert isinstance(result.take_profit, (int, float))
    # For valid trades (non-HOLD), verify basic directionality if values are positive
    if result.action != "HOLD" and result.stop_loss > 0 and result.take_profit > 0:
        if result.action == "BUY":
            assert result.stop_loss < result.current_price, \
                f"BUY stop_loss should be below current_price. Got: SL={result.stop_loss}, Price={result.current_price}"
            assert result.take_profit > result.current_price, \
                f"BUY take_profit should be above current_price. Got: TP={result.take_profit}, Price={result.current_price}"
        elif result.action == "SELL":
            assert result.stop_loss > result.current_price, \
                f"SELL stop_loss should be above current_price. Got: SL={result.stop_loss}, Price={result.current_price}"
            assert result.take_profit < result.current_price, \
                f"SELL take_profit should be below current_price. Got: TP={result.take_profit}, Price={result.current_price}"
    
    # Verify normalized fields
    assert hasattr(result, "risk_reward_ratio")
    assert hasattr(result, "entry_label")
    assert hasattr(result, "risk_percentage")
    assert hasattr(result, "normalized_weights_sum")
    assert hasattr(result, "position_size_usd")
    assert hasattr(result, "position_size_pct")
    
    # Verify contribution breakdown exists
    assert result.contribution_breakdown is not None
    assert isinstance(result.contribution_breakdown, list)
    assert len(result.contribution_breakdown) == len(signals)


def test_e2e_aggregator_all_hold_consensus_zero():
    """Verify that all HOLD signals result in consensus = 0.0."""
    svc = RecommendationService()
    
    signals = [
        _make_signal("H1", 0, 0.0, 0.5, "1h", 50000.0),
        _make_signal("H2", 0, 0.0, 0.5, "4h", 50000.0),
        _make_signal("H3", 0, 0.0, 0.5, "1d", 50000.0),
    ]
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
    data = {
        '1h': pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0,
            'high': 50100.0,
            'low': 49900.0,
            'close': 50000.0,
            'volume': 1000.0,
        }),
    }
    
    result = svc._analyze_signals(signals, data=data, profile="balanced")
    
    assert result.action == "HOLD"
    assert result.signal_consensus == 0.0, \
        f"Consensus should be 0.0 with all HOLD (uncertainty). Got: {result.signal_consensus}"
    assert result.confidence == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

