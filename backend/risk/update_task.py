"""Recurring task to compute and persist live risk metrics and emit alerts."""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from backend.api.routes.risk import get_risk_engine
from backend.repositories.risk_repository import RiskRepository
from backend.api.routes.websocket import broadcast_risk_update, broadcast_alert
from backend.risk.alerts import AlertManager
from backend.observability.alerts import ObservabilityAlertManager, AlertType, AlertSeverity
from backend.observability.metrics import get_metrics_collector


logger = logging.getLogger(__name__)


class RiskUpdateTask:
    """Pulls metrics from the risk engine, persists them, and notifies listeners."""

    def __init__(self, alert_manager: Optional[AlertManager] = None):
        self.repo = RiskRepository()
        self.alert_manager = alert_manager or AlertManager()

    async def run_once(self) -> Optional[int]:
        """Run a single metrics collection cycle.

        Returns inserted record id if persisted, else None.
        """
        try:
            engine = get_risk_engine()
            if engine is None:
                logger.warning("Risk engine not initialized; skipping risk update")
                return None

            # Collect metrics from engine
            metrics_obj = engine.get_risk_metrics()
            metrics: Dict[str, Any] = {
                "timestamp": getattr(metrics_obj, "timestamp", datetime.utcnow()),
                "total_capital": metrics_obj.total_capital,
                "total_exposure": metrics_obj.total_exposure,
                "exposure_pct": metrics_obj.exposure_pct,
                "var_1d_95": metrics_obj.var_1d_95,
                "var_1d_99": metrics_obj.var_1d_99,
                "var_1w_95": metrics_obj.var_1w_95,
                "var_1w_99": metrics_obj.var_1w_99,
                "current_drawdown_pct": metrics_obj.current_drawdown_pct,
                "max_drawdown_pct": metrics_obj.max_drawdown_pct,
                "unrealized_pnl": metrics_obj.unrealized_pnl,
                "daily_pnl": metrics_obj.daily_pnl,
            }

            # Persist
            record_id = self.repo.save_metrics(metrics)
            # Metrics: exposure and VaR snapshot
            try:
                collector = get_metrics_collector()
                collector.record_strategy_metric("system", "pnl", float(metrics.get("daily_pnl", 0.0)))
            except Exception:
                pass

            # Broadcast via WebSocket
            try:
                await broadcast_risk_update(metrics)
            except Exception as e:
                logger.error(f"Failed to broadcast risk update: {e}")

            # Check limits and alert
            try:
                checks = engine.check_risk_limits(metrics_obj)
                for limit_name, result in checks.items():
                    if result.get("violated"):
                        msg = f"{limit_name} violated: current={result.get('current')}, limit={result.get('limit')}"
                        # Slack
                        self.alert_manager.send_slack_alert(
                            title=f"Risk Limit Breach: {limit_name}",
                            message=msg,
                            severity="error",
                        )
                        # WebSocket alert
                        await broadcast_alert("error", f"Risk limit: {limit_name}", msg, details={"checks": checks})
                        # Observability alert
                        try:
                            ObservabilityAlertManager()._process_alert(
                                ObservabilityAlertManager()._create_alert(
                                    AlertType.RISK_LIMIT_VIOLATION,
                                    AlertSeverity.CRITICAL,
                                    f"Risk limit breached: {limit_name}",
                                    msg,
                                    {"checks": checks}
                                )
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Error evaluating risk limits: {e}")

            return record_id
        except Exception as e:
            logger.error(f"Risk update task failed: {e}")
            return None


