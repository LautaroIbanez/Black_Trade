"""Repository for live recommendation snapshots."""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.models.live_results import LiveRecommendation


class LiveResultsRepository:
    def save_snapshot(self, symbol: str, timeframe: str, payload: Dict, db: Session = None) -> int:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = LiveRecommendation(symbol=symbol, timeframe=timeframe, payload=payload)
            db.add(rec)
            db.commit()
            db.refresh(rec)
            return rec.id
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

    def get_latest(self, symbol: str, timeframe: str, limit: int = 1, db: Session = None) -> List[Dict]:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            q = (db.query(LiveRecommendation)
                    .filter(LiveRecommendation.symbol == symbol, LiveRecommendation.timeframe == timeframe)
                    .order_by(LiveRecommendation.created_at.desc())
                    .limit(limit)
                )
            return [r.to_dict() for r in q.all()]
        finally:
            if should_close:
                db.close()



