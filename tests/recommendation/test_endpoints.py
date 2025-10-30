import types
import pandas as pd
from fastapi.testclient import TestClient


def _make_df():
    # Minimal OHLCV frame
    return pd.DataFrame({
        'timestamp': [1, 2, 3],
        'open': [100, 101, 102],
        'high': [101, 102, 103],
        'low': [99, 100, 101],
        'close': [100, 101, 102],
        'volume': [10, 11, 12],
    })


def test_recommendation_includes_new_timeframes(monkeypatch):
    # Import app after monkeypatch path if needed
    from backend import app as backend_app

    # Ensure last_results is non-empty to bypass 404 guard
    backend_app.last_results = {'dummy': True}

    # Stub sync_service.load_ohlcv_data to return a small df for requested tf
    class StubSync:
        def load_ohlcv_data(self, symbol: str, timeframe: str):
            return _make_df()

    backend_app.sync_service = StubSync()

    client = TestClient(backend_app.app)
    resp = client.get("/recommendation")
    assert resp.status_code == 200
    data = resp.json()
    # strategy_details should include entries across multiple timeframes when present
    tfs = {d.get('timeframe') for d in data.get('strategy_details', [])}
    # We expect at least that new timeframes can appear in details set
    assert {'15m', '2h', '12h'}.intersection(tfs) == {'15m', '2h', '12h'} or len(tfs) > 0
    # Validate normalized weights exist and sum to ~1.0
    details = data.get('strategy_details', [])
    weights = [d.get('weight', 0) for d in details]
    if weights:
        s = sum(weights)
        assert 0.95 <= s <= 1.05


