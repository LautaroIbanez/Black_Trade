"""Service to compute live recommendations on new candles and persist results."""
import asyncio
import logging
import os
import time
from typing import Dict, List

from backend.services.market_data_service import MarketDataService
from backend.repositories.live_results_repository import LiveResultsRepository
from backend.observability.metrics import get_metrics_collector
from backend.observability.alerts import ObservabilityAlertManager, AlertType, AlertSeverity
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
from backend.recommendation.live_recommendations_service import live_recommendations_service


logger = logging.getLogger(__name__)


class SignalComputationService:
    """Computes live recommendations per timeframe and stores snapshots."""

    def __init__(self):
        self.market_data = MarketDataService()
        self.live_repo = LiveResultsRepository()
        self.symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
        # Use configured timeframes; computing only those touched is handled by caller
        self.default_timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')

    def _load_data_for_timeframes(self, timeframes: List[str]) -> Dict[str, any]:
        data = {}
        for tf in timeframes:
            df = self.market_data.load_ohlcv_data(self.symbol, tf)
            if not df.empty:
                data[tf] = df
        return data

    async def compute_and_store(self, impacted_timeframes: List[str], max_retries: int = 3) -> bool:
        """Compute recommendation for impacted timeframes and persist snapshots with retries."""
        attempts = 0
        while attempts <= max_retries:
            try:
                t0 = time.perf_counter()
                # Load data
                data = self._load_data_for_timeframes(impacted_timeframes or self.default_timeframes)
                if not data:
                    logger.warning("No data available for signal computation")
                    return False

                # Generate recommendation (balanced by default)
                rec = recommendation_service.generate_recommendation(data, historical_metrics=None, profile=os.getenv('AUTO_ORDER_PROFILE', 'balanced'))

                # Persist snapshot per primary timeframe (choose the highest TF present)
                for tf in data.keys():
                    payload = rec.__dict__ if hasattr(rec, '__dict__') else {}
                    # Normalize enums, objects to JSON-friendly
                    try:
                        self.live_repo.save_snapshot(self.symbol, tf, payload)
                    except Exception as e:
                        logger.error(f"Failed to persist live recommendation for {tf}: {e}")

                # Publish to shared cache for /recommendation endpoint
                try:
                    live_recommendations_service.publish(self.symbol, list(data.keys()), payload)
                except Exception as e:
                    logger.error(f"Failed to publish live recommendation: {e}")

                # Metrics
                try:
                    get_metrics_collector().record_strategy_metric('system', 'generation_time', (time.perf_counter() - t0) * 1000.0)
                except Exception:
                    pass

                return True
            except Exception as e:
                attempts += 1
                backoff = min(2 ** attempts, 30)
                logger.error(f"Signal computation failed (attempt {attempts}/{max_retries}): {e}")
                if attempts > max_retries:
                    try:
                        ObservabilityAlertManager()._process_alert(
                            ObservabilityAlertManager()._create_alert(
                                AlertType.STRATEGY_DEGRADATION,
                                AlertSeverity.WARNING,
                                "Signal computation repeatedly failed",
                                str(e),
                                {"attempts": attempts}
                            )
                        )
                    except Exception:
                        pass
                    return False
                await asyncio.sleep(backoff)


