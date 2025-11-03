"""Task to convert live recommendations into executable orders automatically."""
import os
import logging
from typing import Optional

from backend.services.market_data_service import MarketDataService
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
from recommendation.orchestrator import SignalOrchestrator
from backend.api.routes.execution import get_execution_coordinator


logger = logging.getLogger(__name__)


class RecommendationExecutionTask:
    def __init__(self, orchestrator: Optional[SignalOrchestrator] = None):
        self.market_data = MarketDataService()
        self.orchestrator = orchestrator or SignalOrchestrator()

    async def run_once(self) -> Optional[str]:
        try:
            symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')[0]
            timeframes = os.getenv('TIMEFRAMES', '1h').split(',')

            # Load latest data for each timeframe (simple approach)
            current_data = {}
            for tf in timeframes:
                df = self.market_data.load_ohlcv_data(symbol, tf)
                if not df.empty:
                    current_data[tf] = df

            if not current_data:
                logger.warning("No current data available for recommendation execution")
                return None

            # Use previously ranked results if available via registry; fall back to enabled strategies
            strategies = strategy_registry.get_enabled_strategies()

            # Generate recommendation
            rec = recommendation_service.generate_recommendation(current_data, {}, profile=os.getenv('AUTO_ORDER_PROFILE', 'balanced'))

            min_conf = float(os.getenv('AUTO_ORDER_MIN_CONFIDENCE', '0.6'))
            if rec.confidence < min_conf or rec.action.lower() not in ("buy", "sell"):
                return None

            # Convert to order
            order = self.orchestrator.recommendation_to_order(rec, symbol=symbol)
            if not order:
                return None

            # Execute via coordinator with conflict rules
            coordinator = get_execution_coordinator()
            success, order_id, error = coordinator.execute_order(order)
            if success:
                logger.info(f"Auto order submitted: {order_id}")
                return order_id
            else:
                logger.info(f"Auto order blocked: {error}")
                return None
        except Exception as e:
            logger.error(f"Recommendation execution error: {e}")
            return None


