"""SQLAlchemy models for execution journal."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from sqlalchemy.sql import func

from backend.models.base import Base


class JournalEntry(Base):
    __tablename__ = 'journal_entries'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    type = Column(String(50), index=True)
    order_id = Column(String(100), index=True, nullable=True)
    user = Column(String(100), default='system')
    details = Column(JSON)

    __table_args__ = (
        Index('idx_journal_type_time', 'type', 'timestamp'),
        Index('idx_journal_order_time', 'order_id', 'timestamp'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'type': self.type,
            'order_id': self.order_id,
            'user': self.user,
            'details': self.details or {},
        }


