"""Repository for persistent user management."""
from typing import Optional
from sqlalchemy.orm import Session
import uuid

from backend.db.session import get_db_session
from backend.models.user import User


class UserRepository:
    """Repository for user persistence operations."""
    
    def find_by_email(self, email: str, db: Session = None) -> Optional[User]:
        """Find user by email."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            if should_close:
                db.close()
    
    def find_by_user_id(self, user_id: str, db: Session = None) -> Optional[User]:
        """Find user by user_id."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            return db.query(User).filter(User.user_id == user_id).first()
        finally:
            if should_close:
                db.close()
    
    def find_by_username(self, username: str, db: Session = None) -> Optional[User]:
        """Find user by username."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            return db.query(User).filter(User.username == username).first()
        finally:
            if should_close:
                db.close()
    
    def create_or_get(self, username: str, role: str, email: Optional[str] = None, db: Session = None) -> User:
        """Create a new user or return existing user if found by email or username."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            # If email provided, try to find existing user by email first
            if email:
                existing = self.find_by_email(email, db)
                if existing:
                    # Update username and role if changed
                    existing.username = username
                    existing.role = role
                    db.commit()
                    db.refresh(existing)
                    return existing
            
            # Try to find by username if no email match
            existing = self.find_by_username(username, db)
            if existing:
                # Update email if provided and not set
                if email and not existing.email:
                    existing.email = email
                # Update role if changed
                existing.role = role
                db.commit()
                db.refresh(existing)
                return existing
            
            # Create new user with persistent user_id
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            user = User(user_id=user_id, username=username, email=email, role=role)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
    
    def update_user(self, user_id: str, username: Optional[str] = None, role: Optional[str] = None, email: Optional[str] = None, db: Session = None) -> Optional[User]:
        """Update user attributes."""
        should_close = db is None
        if db is None:
            db = get_db_session()
        try:
            user = self.find_by_user_id(user_id, db)
            if not user:
                return None
            if username is not None:
                user.username = username
            if role is not None:
                user.role = role
            if email is not None:
                user.email = email
            db.commit()
            db.refresh(user)
            return user
        except Exception:
            db.rollback()
            raise
        finally:
            if should_close:
                db.close()
