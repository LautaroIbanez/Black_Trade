"""Repository to store and query journal entries."""
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.models.journal import JournalEntry


class JournalRepository:
    def add_entry(self, entry_type: str, order_id: Optional[str], user: str, details: Dict, db: Session = None) -> int:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            entry = JournalEntry(type=entry_type, order_id=order_id, user=user or 'system', details=details or {})
            db.add(entry)
            db.commit()
            db.refresh(entry)
            return entry.id
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

    def get_entries(self, order_id: Optional[str] = None, entry_type: Optional[str] = None, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 100, db: Session = None) -> List[Dict]:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            q = db.query(JournalEntry)
            if order_id:
                q = q.filter(JournalEntry.order_id == order_id)
            if entry_type:
                q = q.filter(JournalEntry.type == entry_type)
            if start_time:
                q = q.filter(JournalEntry.timestamp >= start_time)
            if end_time:
                q = q.filter(JournalEntry.timestamp <= end_time)
            q = q.order_by(JournalEntry.timestamp.desc()).limit(limit)
            return [e.to_dict() for e in q.all()]
        finally:
            if should_close:
                db.close()



