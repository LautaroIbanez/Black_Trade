"""Periodic observability checks for freshness and hit ratio with alerts."""
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text

from backend.db.session import db_session
from backend.observability.alerts import ObservabilityAlertManager, AlertType, AlertSeverity


logger = logging.getLogger(__name__)


class ObservabilityMonitorTask:
    def __init__(self, freshness_minutes: int = 10, min_hit_ratio: float = 0.4):
        self.freshness_minutes = freshness_minutes
        self.min_hit_ratio = min_hit_ratio
        self.alerts = ObservabilityAlertManager()

    async def run_once(self):
        try:
            self._check_freshness()
            self._check_hit_ratio()
        except Exception as e:
            logger.error(f"Observability monitor error: {e}")

    def _check_freshness(self):
        cutoff = datetime.utcnow() - timedelta(minutes=self.freshness_minutes)
        with db_session() as db:
            last = db.execute(text("SELECT max(created_at) FROM live_recommendations")).scalar()
        if not last or last < cutoff:
            self.alerts._process_alert(
                self.alerts._create_alert(
                    AlertType.SERVICE_DOWN,
                    AlertSeverity.WARNING,
                    "Stale recommendations",
                    f"No live recommendations since {last}",
                    {"cutoff_minutes": self.freshness_minutes}
                )
            )

    def _check_hit_ratio(self):
        # Last 100 decided recommendations
        with db_session() as db:
            rows = db.execute(text("""
                SELECT outcome FROM recommendations_log
                WHERE outcome IS NOT NULL
                ORDER BY decided_at DESC
                LIMIT 100
            """)).fetchall()
        if not rows:
            return
        total = len(rows)
        hits = len([r[0] for r in rows if str(r[0]).lower() == 'win'])
        ratio = hits / total if total > 0 else 0.0
        if ratio < self.min_hit_ratio:
            self.alerts._process_alert(
                self.alerts._create_alert(
                    AlertType.STRATEGY_DEGRADATION,
                    AlertSeverity.WARNING,
                    "Low hit ratio",
                    f"Hit ratio {ratio:.2f} over last {total} recommendations",
                    {"ratio": ratio, "total": total}
                )
            )


