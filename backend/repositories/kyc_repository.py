"""Repository for KYC user state."""
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.models.kyc import KYCUser


class KYCRepository:
    def upsert(self, user_id: str, name: str, email: str, country: str, verified: bool = False, verified_at: Optional[datetime] = None, db: Session = None) -> bool:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = db.query(KYCUser).filter(KYCUser.user_id == user_id).first()
            if rec is None:
                rec = KYCUser(user_id=user_id, name=name, email=email, country=country, verified=verified, verified_at=verified_at)
                db.add(rec)
            else:
                rec.name = name
                rec.email = email
                rec.country = country
                if verified:
                    rec.verified = True
                    rec.verified_at = verified_at or datetime.utcnow()
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

    def is_verified(self, user_id: str, db: Session = None) -> bool:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = db.query(KYCUser).filter(KYCUser.user_id == user_id).first()
            return bool(rec and rec.verified)
        finally:
            if should_close:
                db.close()



