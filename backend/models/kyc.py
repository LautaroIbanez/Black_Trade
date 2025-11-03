"""KYC user verification state model."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from backend.models.base import Base


class KYCUser(Base):
    __tablename__ = 'kyc_users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True, index=True)
    name = Column(String(200))
    email = Column(String(200), index=True)
    country = Column(String(50))
    verified = Column(Boolean, default=False, index=True)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'country': self.country,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


