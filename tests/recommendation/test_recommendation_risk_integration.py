import pytest

from recommendation.engine.prioritizer import RecommendationPrioritizer


def test_prioritizer_includes_risk_fields(monkeypatch):
    pr = RecommendationPrioritizer()
    items = pr.generate_live_list(profile='balanced')
    # If no data available, items may be empty; skip assertions
    if not items:
        pytest.skip('No data available for prioritizer test')
    item = items[0]
    # Ensure risk fields are present
    assert 'suggested_position_size_usd' in item
    assert 'risk_metrics' in item
    assert 'risk_limits' in item
    assert 'risk_limit_checks' in item


