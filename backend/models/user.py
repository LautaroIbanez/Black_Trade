"""Persistent user model for authentication."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
import uuid

from backend.models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=True)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
