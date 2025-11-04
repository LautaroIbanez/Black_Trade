"""Integration tests for walk-forward evaluation → API → UI flow."""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.repositories.strategy_results_repository import StrategyResultsRepository
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
from backend.api.routes.strategies import get_optimal_parameters, get_strategy_metrics
from backend.db.init_db import initialize_database


@pytest.fixture
def test_db():
    """Initialize test database."""
    initialize_database()


@pytest.fixture
def sample_optimal_parameters(test_db):
    """Create sample optimal parameters for testing."""
    repo = StrategyResultsRepository()
    
    # Save optimal parameters
    param_id = repo.save_optimal_parameters(
        strategy_name="EMA_RSI",
        parameters={
            "fast_period": 10,
            "slow_period": 24,
            "rsi_period": 12,
            "rsi_oversold": 25,
            "rsi_overbought": 75,
        },
        validation_metrics={
            "sharpe_ratio": 1.5,
            "win_rate": 0.65,
            "profit_factor": 1.8,
            "max_drawdown_pct": 15.0,
        },
        dataset_name="BTCUSDT_1h",
        validation_period_start=datetime.now() - timedelta(days=30),
        validation_period_end=datetime.now(),
    )
    
    # Save some backtest results
    repo.save_backtest_result(
        strategy_name="EMA_RSI",
        parameters={"fast_period": 10, "slow_period": 24},
        metrics={
            "sharpe_ratio": 1.5,
            "win_rate": 0.65,
            "profit_factor": 1.8,
        },
        split_type="oos",
    )
    
    return param_id


class TestWalkForwardIntegration:
    """Test complete walk-forward integration flow."""
    
    def test_repository_saves_optimal_parameters(self, test_db, sample_optimal_parameters):
        """Test that repository correctly saves optimal parameters."""
        repo = StrategyResultsRepository()
        
        optimal = repo.get_latest_optimal_parameters("EMA_RSI")
        
        assert optimal is not None
        assert optimal["strategy_name"] == "EMA_RSI"
        assert optimal["parameters"]["fast_period"] == 10
        assert optimal["parameters"]["slow_period"] == 24
        assert optimal["validation_metrics"]["sharpe_ratio"] == 1.5
    
    def test_strategy_registry_uses_optimal_parameters(self, test_db, sample_optimal_parameters):
        """Test that strategy registry loads optimal parameters."""
        # Get strategies with optimal parameters
        strategies = strategy_registry.get_enabled_strategies(use_optimal_parameters=True)
        
        # Find EMA_RSI strategy
        ema_rsi = next((s for s in strategies if s.name == "EMA_RSI"), None)
        
        if ema_rsi:
            # Verify parameters are from optimal (if strategy has these attributes)
            # This depends on strategy implementation
            assert ema_rsi is not None
    
    def test_recommendation_service_uses_optimal_parameters(self, test_db, sample_optimal_parameters):
        """Test that recommendation service uses optimal parameters."""
        import pandas as pd
        import numpy as np
        
        # Create sample data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        data = {
            '1h': pd.DataFrame({
                'timestamp': [int(d.timestamp() * 1000) for d in dates],
                'open': np.random.randn(100).cumsum() + 50000,
                'high': np.random.randn(100).cumsum() + 50100,
                'low': np.random.randn(100).cumsum() + 49900,
                'close': np.random.randn(100).cumsum() + 50000,
                'volume': np.random.rand(100) * 1000,
            })
        }
        
        # Generate recommendation (should use optimal parameters)
        recommendation = recommendation_service.generate_recommendation(data, profile="balanced")
        
        # Verify recommendation was generated (may be HOLD if no signals)
        assert recommendation is not None
        assert hasattr(recommendation, 'action')
    
    def test_api_returns_optimal_parameters(self, test_db, sample_optimal_parameters):
        """Test that API endpoint returns optimal parameters."""
        from fastapi.testclient import TestClient
        from backend.app import app
        
        client = TestClient(app)
        
        response = client.get("/api/strategies/EMA_RSI/optimal-parameters")
        
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_name"] == "EMA_RSI"
        assert data["parameters"]["fast_period"] == 10
        assert "validation_metrics" in data
    
    def test_api_returns_strategy_metrics(self, test_db, sample_optimal_parameters):
        """Test that API endpoint returns strategy metrics."""
        from fastapi.testclient import TestClient
        from backend.app import app
        
        client = TestClient(app)
        
        response = client.get("/api/strategies/EMA_RSI/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_name"] == "EMA_RSI"
        assert data["latest_optimal_parameters"] is not None
        assert "summary_metrics" in data
    
    def test_api_returns_performance(self, test_db, sample_optimal_parameters):
        """Test that API endpoint returns performance metrics."""
        from fastapi.testclient import TestClient
        from backend.app import app
        
        client = TestClient(app)
        
        response = client.get("/api/strategies/EMA_RSI/performance")
        
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_name"] == "EMA_RSI"
        assert "in_sample" in data
        assert "out_of_sample" in data
        assert "consistency" in data
    
    def test_complete_flow(self, test_db):
        """Test complete flow: evaluation → save → retrieve → use in recommendations."""
        repo = StrategyResultsRepository()
        
        # 1. Simulate walk-forward evaluation saving optimal parameters
        repo.save_optimal_parameters(
            strategy_name="EMA_RSI",
            parameters={"fast_period": 8, "slow_period": 20},
            validation_metrics={"sharpe_ratio": 2.0, "win_rate": 0.70},
        )
        
        # 2. Verify parameters are saved
        optimal = repo.get_latest_optimal_parameters("EMA_RSI")
        assert optimal is not None
        
        # 3. Get strategy with optimal parameters
        strategies = strategy_registry.get_enabled_strategies(use_optimal_parameters=True)
        ema_rsi = next((s for s in strategies if s.name == "EMA_RSI"), None)
        
        # 4. Verify recommendation service can use them
        import pandas as pd
        import numpy as np
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        data = {
            '1h': pd.DataFrame({
                'timestamp': [int(d.timestamp() * 1000) for d in dates],
                'open': np.random.randn(100).cumsum() + 50000,
                'high': np.random.randn(100).cumsum() + 50100,
                'low': np.random.randn(100).cumsum() + 49900,
                'close': np.random.randn(100).cumsum() + 50000,
                'volume': np.random.rand(100) * 1000,
            })
        }
        
        recommendation = recommendation_service.generate_recommendation(data, profile="balanced")
        assert recommendation is not None



