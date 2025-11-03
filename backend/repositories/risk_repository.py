"""Repository for persisting and retrieving risk metrics."""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import db_session
from backend.models.risk_metrics import RiskMetric


class RiskRepository:
    """Persistence layer for risk metrics time series."""

    def save_metrics(self, metrics: Dict[str, Any], db: Session = None) -> int:
        """Persist a metrics snapshot to the database.

        Returns the inserted record id.
        """
        should_close = db is None
        if db is None:
            db = next(db_session())

        try:
            record = RiskMetric(
                timestamp=metrics.get("timestamp", datetime.utcnow()),
                total_capital=metrics.get("total_capital"),
                total_exposure=metrics.get("total_exposure"),
                exposure_pct=metrics.get("exposure_pct"),
                var_1d_95=metrics.get("var_1d_95"),
                var_1d_99=metrics.get("var_1d_99"),
                var_1w_95=metrics.get("var_1w_95"),
                var_1w_99=metrics.get("var_1w_99"),
                current_drawdown_pct=metrics.get("current_drawdown_pct"),
                max_drawdown_pct=metrics.get("max_drawdown_pct"),
                unrealized_pnl=metrics.get("unrealized_pnl"),
                daily_pnl=metrics.get("daily_pnl"),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record.id
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

    def get_latest(self, limit: int = 1, db: Session = None) -> List[Dict[str, Any]]:
        """Fetch the latest N risk metric records as dicts."""
        should_close = db is None
        if db is None:
            db = next(db_session())
        try:
            q = db.query(RiskMetric).order_by(RiskMetric.timestamp.desc()).limit(limit).all()
            return [r.to_dict() for r in q]
        finally:
            if should_close:
                db.close()


