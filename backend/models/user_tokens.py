"""Models to persist issued JWT access and refresh tokens."""
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.sql import func

from backend.models.base import Base


class UserToken(Base):
    __tablename__ = 'user_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), index=True)
    token = Column(String(512), unique=True, index=True)
    token_type = Column(String(20))  # access|refresh
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_user_token_user_type', 'user_id', 'token_type'),
    )


