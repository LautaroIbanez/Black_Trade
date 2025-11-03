"""Model for storing live recommendation snapshots per timeframe."""
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func

from backend.models.base import Base


class LiveRecommendation(Base):
    __tablename__ = 'live_recommendations'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), index=True, nullable=False)
    timeframe = Column(String(20), index=True, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'payload': self.payload,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


