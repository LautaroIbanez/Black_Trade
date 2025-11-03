"""Models for human-in-the-loop recommendations tracking."""
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

from backend.models.base import Base


class RecommendationLog(Base):
    __tablename__ = 'recommendations_log'

    id = Column(Integer, primary_key=True)
    status = Column(String(20), index=True, default='suggested')  # suggested|accepted|rejected
    user_id = Column(String(100), index=True, nullable=True)
    symbol = Column(String(50), index=True)
    timeframe = Column(String(20), index=True)
    confidence = Column(String(20))
    risk_level = Column(String(20))
    payload = Column(JSON)  # full recommendation snapshot
    checklist = Column(JSON)  # pre/post trade checklist state
    notes = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'status': self.status,
            'user_id': self.user_id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'confidence': self.confidence,
            'risk_level': self.risk_level,
            'payload': self.payload,
            'checklist': self.checklist,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


