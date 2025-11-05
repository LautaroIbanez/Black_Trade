"""Tests for chart API endpoints."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from backend.app import app
from backend.services.market_data_service import MarketDataService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_market_data_service():
    """Mock market data service."""
    with patch('backend.api.routes.chart.market_data_service') as mock_service:
        yield mock_service


def test_chart_endpoint_empty_dataframe(mock_market_data_service, client):
    """Test chart endpoint with empty DataFrame."""
    # Mock empty DataFrame
    mock_market_data_service.load_ohlcv_data.return_value = pd.DataFrame(
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    
    response = client.get("/api/chart/BTCUSDT/1h")
    
    assert response.status_code == 404
    assert "Empty dataset" in response.json()["detail"]


def test_chart_endpoint_with_int_timestamps(mock_market_data_service, client):
    """Test chart endpoint with int timestamps (milliseconds)."""
    # Create DataFrame with int timestamps (milliseconds)
    now = int(datetime.now().timestamp() * 1000)
    timestamps = [now - (i * 3600 * 1000) for i in range(99, -1, -1)]  # Last 100 hours
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100.0] * 100,
        'high': [110.0] * 100,
        'low': [90.0] * 100,
        'close': [105.0] * 100,
        'volume': [1000.0] * 100,
    })
    
    mock_market_data_service.load_ohlcv_data.return_value = df
    
    response = client.get("/api/chart/BTCUSDT/1h?limit=100&include_signals=false&include_recommendation=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["symbol"] == "BTCUSDT"
    assert data["timeframe"] == "1h"
    assert len(data["candles"]) == 100
    assert all(isinstance(c["timestamp"], int) for c in data["candles"])
    assert all(c["timestamp"] > 0 for c in data["candles"])


def test_chart_endpoint_with_datetime64_timestamps(mock_market_data_service, client):
    """Test chart endpoint with datetime64 timestamps."""
    # Create DataFrame with datetime64 timestamps
    now = datetime.now()
    timestamps = pd.date_range(end=now, periods=50, freq='1H')
    
    df = pd.DataFrame({
        'timestamp': timestamps,  # This will be datetime64
        'open': [200.0] * 50,
        'high': [210.0] * 50,
        'low': [190.0] * 50,
        'close': [205.0] * 50,
        'volume': [2000.0] * 50,
    })
    
    mock_market_data_service.load_ohlcv_data.return_value = df
    
    response = client.get("/api/chart/ETHUSDT/4h?limit=50&include_signals=false&include_recommendation=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["symbol"] == "ETHUSDT"
    assert data["timeframe"] == "4h"
    assert len(data["candles"]) == 50
    assert all(isinstance(c["timestamp"], int) for c in data["candles"])
    assert all(c["timestamp"] > 0 for c in data["candles"])
    # Verify datetime string is ISO format
    assert all("T" in c["datetime"] or " " in c["datetime"] for c in data["candles"])


def test_chart_endpoint_with_pandas_timestamp(mock_market_data_service, client):
    """Test chart endpoint with pandas Timestamp objects."""
    # Create DataFrame with pandas Timestamp objects
    now = pd.Timestamp.now()
    timestamps = [now - pd.Timedelta(hours=i) for i in range(10, 0, -1)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [300.0] * 10,
        'high': [310.0] * 10,
        'low': [290.0] * 10,
        'close': [305.0] * 10,
        'volume': [3000.0] * 10,
    })
    
    mock_market_data_service.load_ohlcv_data.return_value = df
    
    response = client.get("/api/chart/ADAUSDT/1d?limit=10&include_signals=false&include_recommendation=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["candles"]) == 10
    assert all(isinstance(c["timestamp"], int) for c in data["candles"])
    assert all(isinstance(c["datetime"], str) for c in data["candles"])


def test_chart_endpoint_invalid_timeframe(mock_market_data_service, client):
    """Test chart endpoint with invalid timeframe."""
    response = client.get("/api/chart/BTCUSDT/invalid_tf")
    
    assert response.status_code == 400
    assert "Invalid timeframe" in response.json()["detail"]


def test_chart_endpoint_metadata(mock_market_data_service, client):
    """Test chart endpoint includes metadata."""
    now = int(datetime.now().timestamp() * 1000)
    timestamps = [now - (i * 3600 * 1000) for i in range(24, -1, -1)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100.0] * 25,
        'high': [110.0] * 25,
        'low': [90.0] * 25,
        'close': [105.0] * 25,
        'volume': [1000.0] * 25,
    })
    
    mock_market_data_service.load_ohlcv_data.return_value = df
    
    response = client.get("/api/chart/BTCUSDT/1h?limit=25&include_signals=false&include_recommendation=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "metadata" in data
    assert data["metadata"]["total_candles"] == 25
    assert "date_range" in data["metadata"]
    assert "timeframe_minutes" in data["metadata"]
    assert "signals_count" in data["metadata"]


def test_chart_endpoint_current_price(mock_market_data_service, client):
    """Test chart endpoint includes current price."""
    now = int(datetime.now().timestamp() * 1000)
    timestamps = [now - (i * 3600 * 1000) for i in range(4, -1, -1)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [110.0] * 5,
        'low': [90.0] * 5,
        'close': [105.0, 106.0, 107.0, 108.0, 109.0],  # Last close is 109.0
        'volume': [1000.0] * 5,
    })
    
    mock_market_data_service.load_ohlcv_data.return_value = df
    
    response = client.get("/api/chart/BTCUSDT/1h?limit=5&include_signals=false&include_recommendation=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["current_price"] == 109.0  # Last close price


def test_chart_endpoint_limit_parameter(mock_market_data_service, client):
    """Test chart endpoint respects limit parameter."""
    now = int(datetime.now().timestamp() * 1000)
    timestamps = [now - (i * 3600 * 1000) for i in range(99, -1, -1)]
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100.0] * 100,
        'high': [110.0] * 100,
        'low': [90.0] * 100,
        'close': [105.0] * 100,
        'volume': [1000.0] * 100,
    })
    
    mock_market_data_service.load_ohlcv_data.return_value = df
    
    # Request only 10 candles
    response = client.get("/api/chart/BTCUSDT/1h?limit=10&include_signals=false&include_recommendation=false")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["candles"]) == 10
    assert data["metadata"]["total_candles"] == 10

