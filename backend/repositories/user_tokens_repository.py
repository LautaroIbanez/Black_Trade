"""Repository for persisting user tokens (access/refresh)."""
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import db_session
from backend.models.user_tokens import UserToken


class UserTokensRepository:
    def save(self, user_id: str, token: str, token_type: str, expires_at: Optional[datetime] = None, db: Session = None) -> int:
        should_close = db is None
        if db is None:
            db = next(db_session())
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
            db = next(db_session())
        try:
            return db.query(UserToken).filter(UserToken.token == token).first()
        finally:
            if should_close:
                db.close()


