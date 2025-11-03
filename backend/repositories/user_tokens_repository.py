"""Repository for persisting user tokens (access/refresh)."""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.models.user_tokens import UserToken


class UserTokensRepository:
    def save(self, user_id: str, token: str, token_type: str, expires_at: Optional[datetime] = None, db: Session = None) -> int:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = UserToken(user_id=user_id, token=token, token_type=token_type, expires_at=expires_at)
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

    def get(self, token: str, db: Session = None) -> Optional[UserToken]:
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            return db.query(UserToken).filter(UserToken.token == token).first()
        finally:
            if should_close:
                db.close()

    def revoke(self, token: str, db: Session = None) -> bool:
        """Revoke a token by deleting it from the database."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            rec = db.query(UserToken).filter(UserToken.token == token).first()
            if rec:
                db.delete(rec)
                db.commit()
                return True
            return False
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

    def revoke_all_for_user(self, user_id: str, db: Session = None) -> int:
        """Revoke all tokens for a user. Returns count of revoked tokens."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            count = db.query(UserToken).filter(UserToken.user_id == user_id).delete()
            db.commit()
            return count
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()

    def is_expired(self, token: str, db: Session = None) -> bool:
        """Check if a token has expired."""
        rec = self.get(token, db)
        if not rec or not rec.expires_at:
            return False
        return datetime.utcnow() > rec.expires_at



