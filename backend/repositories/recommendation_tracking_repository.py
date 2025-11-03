"""Repository for recommendation tracking (accept/reject/outcome)."""
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.models.recommendations import RecommendationLog


class RecommendationTrackingRepository:
    def create(self, status: str, symbol: str, timeframe: str, payload: Dict, user_id: Optional[str] = None, checklist: Optional[Dict] = None, notes: Optional[str] = None) -> int:
        should_close = True
        db = get_db_session()
        try:
            rec = RecommendationLog(status=status, symbol=symbol, timeframe=timeframe, payload=payload, user_id=user_id, checklist=checklist or {}, notes=notes)
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

    def update(self, rec_id: int, status: Optional[str] = None, checklist: Optional[Dict] = None, outcome: Optional[str] = None, realized_pnl: Optional[float] = None, notes: Optional[str] = None) -> bool:
        should_close = True
        db = get_db_session()
        try:
            rec = db.query(RecommendationLog).filter(RecommendationLog.id == rec_id).first()
            if not rec:
                return False
            if status:
                rec.status = status
            if checklist is not None:
                rec.checklist = checklist
            if notes is not None:
                rec.notes = notes
            if outcome is not None:
                rec.outcome = outcome
                rec.realized_pnl = realized_pnl
                rec.decided_at = datetime.utcnow()
            db.commit()
            return True
        finally:
            if should_close:
                db.close()

    def history(self, limit: int = 50) -> List[Dict]:
        should_close = True
        db = get_db_session()
        try:
            rows = db.query(RecommendationLog).order_by(RecommendationLog.created_at.desc()).limit(limit).all()
            return [r.to_dict() for r in rows]
        finally:
            if should_close:
                db.close()

    def get_metrics(self, days: int = 30) -> Dict:
        """Calculate hit ratio and other metrics from tracked recommendations."""
        should_close = True
        db = get_db_session()
        try:
            from sqlalchemy import func, and_
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            total = db.query(func.count(RecommendationLog.id)).filter(RecommendationLog.status.in_(['accepted', 'rejected'])).scalar() or 0
            
            accepted = db.query(func.count(RecommendationLog.id)).filter(RecommendationLog.status == 'accepted').scalar() or 0
            
            with_outcome = db.query(func.count(RecommendationLog.id)).filter(
                RecommendationLog.status == 'accepted',
                RecommendationLog.outcome.isnot(None)
            ).scalar() or 0
            
            wins = db.query(func.count(RecommendationLog.id)).filter(
                RecommendationLog.status == 'accepted',
                RecommendationLog.outcome == 'win'
            ).scalar() or 0
            
            total_pnl = db.query(func.sum(RecommendationLog.realized_pnl)).filter(
                RecommendationLog.status == 'accepted',
                RecommendationLog.realized_pnl.isnot(None)
            ).scalar() or 0.0
            
            return {
                'total_decisions': total,
                'accepted': accepted,
                'rejected': total - accepted,
                'accepted_rate': accepted / total if total > 0 else 0,
                'tracked_outcomes': with_outcome,
                'wins': wins,
                'losses': (db.query(func.count(RecommendationLog.id)).filter(
                    RecommendationLog.status == 'accepted',
                    RecommendationLog.outcome == 'loss'
                ).scalar() or 0),
                'hit_ratio': wins / with_outcome if with_outcome > 0 else 0,
                'total_realized_pnl': float(total_pnl),
            }
        finally:
            if should_close:
                db.close()



