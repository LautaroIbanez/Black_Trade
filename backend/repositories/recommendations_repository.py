"""Repository for human-in-the-loop recommendation tracking."""
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.models.recommendations import RecommendationLog


class RecommendationsRepository:
    def create(self, status: str, symbol: str, timeframe: str, confidence: str, risk_level: str, payload: Dict, checklist: Dict = None, user_id: Optional[str] = None, notes: Optional[str] = None, db: Session = None) -> int:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = RecommendationLog(status=status, symbol=symbol, timeframe=timeframe, confidence=confidence, risk_level=risk_level, payload=payload, checklist=checklist or {}, user_id=user_id, notes=notes)
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

    def update_status(self, rec_id: int, status: str, checklist: Dict = None, notes: Optional[str] = None, outcome: Optional[str] = None, realized_pnl: Optional[float] = None, db: Session = None) -> bool:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = db.query(RecommendationLog).filter(RecommendationLog.id == rec_id).first()
            if not rec:
                return False
            rec.status = status
            if checklist is not None:
                rec.checklist = checklist
            if notes is not None:
                rec.notes = notes
            if outcome is not None:
                rec.outcome = outcome
                rec.realized_pnl = realized_pnl
                from datetime import datetime
                rec.decided_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            if should_close:
                db.close()

    def list_recent(self, limit: int = 20, db: Session = None) -> List[Dict]:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            q = db.query(RecommendationLog).order_by(RecommendationLog.created_at.desc()).limit(limit)
            return [r.to_dict() for r in q.all()]
        finally:
            if should_close:
                db.close()



