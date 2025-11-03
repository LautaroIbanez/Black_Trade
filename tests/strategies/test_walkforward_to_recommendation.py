import os
import pytest

from backend.repositories.strategy_results_repository import StrategyResultsRepository
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
from backend.services.market_data_service import MarketDataService


def test_recommendation_uses_optimal_parameters(monkeypatch):
    # Save a fake optimal parameter set
    repo = StrategyResultsRepository()
    opt_id = repo.save_optimal_parameters(
        strategy_name="EMA_RSI",
        parameters={"fast_period": 10, "slow_period": 22, "rsi_period": 12, "rsi_oversold": 28, "rsi_overbought": 72, "signal_persistence": 2},
        validation_metrics={"sharpe_ratio": 1.2},
        dataset_name="BTCUSDT_1h",
    )
    assert opt_id > 0

    # Ensure registry pulls optimal params
    cfg = strategy_registry.get_strategy_config("EMA_RSI", use_optimal=True)
    assert cfg is not None
    assert cfg.parameters.get("fast_period") == 10

    # Run a recommendation over available data (may be empty in CI)
    data = {}
    mds = MarketDataService()
    df = mds.load_ohlcv_data(os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0], os.getenv('WF_TIMEFRAME', '1h'))
    if not df.empty:
        data[os.getenv('WF_TIMEFRAME', '1h')] = df
        rec = recommendation_service.generate_recommendation(data, historical_metrics=None, profile="balanced")
        assert rec is not None


