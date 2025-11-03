"""Scheduled task to run walk-forward optimization and persist optimal parameters."""
import logging
import os
from datetime import datetime
from typing import Dict, Any

import pandas as pd

from backtest.evaluation.evaluator import StrategyEvaluator
from strategies.strategy_config import EMARSIConfig
from strategies.ema_rsi_strategy import EMARSIStrategy
from backend.services.market_data_service import MarketDataService
from backend.repositories.strategy_results_repository import StrategyResultsRepository


logger = logging.getLogger(__name__)


class WalkforwardOptimizationTask:
    def __init__(self):
        self.market_data = MarketDataService()
        self.results_repo = StrategyResultsRepository()
        self.symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
        self.timeframe = os.getenv('WF_TIMEFRAME', '1h')

    def _load_dataset(self) -> pd.DataFrame:
        return self.market_data.load_ohlcv_data(self.symbol, self.timeframe)

    async def run_once(self) -> bool:
        try:
            df = self._load_dataset()
            if df.empty:
                logger.warning("Walk-forward skipped: dataset empty")
                return False

            # Strategy: EMA_RSI (extendable to others later)
            ema_cfg = EMARSIConfig(strategy_name="EMA_RSI", parameters={})
            param_space = ema_cfg.get_parameter_space()

            evaluator = StrategyEvaluator()
            wf_res = evaluator.wf_engine.run_walk_forward(EMARSIStrategy, df, param_space)

            # Extract best parameters from OOS summary if present; fallback to first fold
            best_params: Dict[str, Any] = wf_res.get('best_parameters') or wf_res.get('oos_best_parameters') or {}
            validation_metrics: Dict[str, Any] = wf_res.get('oos_metrics') or wf_res.get('summary', {})
            train_metrics: Dict[str, Any] = wf_res.get('is_metrics') or {}
            period_start: datetime = wf_res.get('period_start')
            period_end: datetime = wf_res.get('period_end')

            if not best_params:
                logger.warning("Walk-forward produced no best parameters; skipping save")
                return False

            self.results_repo.save_optimal_parameters(
                strategy_name="EMA_RSI",
                parameters=best_params,
                validation_metrics=validation_metrics,
                dataset_name=f"{self.symbol}_{self.timeframe}",
                validation_period_start=period_start,
                validation_period_end=period_end,
                train_metrics=train_metrics,
            )
            logger.info("Walk-forward optimal parameters saved for EMA_RSI")
            return True
        except Exception as e:
            logger.error(f"Walk-forward optimization failed: {e}")
            return False


