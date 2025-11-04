"""High-level authentication service issuing JWT access/refresh and persisting them."""
import os
from datetime import datetime, timedelta
from typing import Tuple, Optional

from backend.auth.permissions import AuthService, Role, get_auth_service, User as AuthUser
from backend.repositories.user_tokens_repository import UserTokensRepository
from backend.repositories.user_repository import UserRepository


class TokenPair:
    def __init__(self, access_token: str, refresh_token: str, user_id: str, role: str, username: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.role = role
        self.username = username


class AppAuthService:
    def __init__(self):
        self.repo = UserTokensRepository()
        self.user_repo = UserRepository()
        try:
            import jwt  # type: ignore
            self._jwt = jwt
        except Exception:
            self._jwt = None
        self.secret = os.getenv('JWT_SECRET', 'dev_secret')

    @property
    def auth(self):
        # Lazy load auth service to avoid circular dependency
        return get_auth_service()

    def issue_tokens(self, username: str, role: Role, email: Optional[str] = None) -> TokenPair:
        """Issue tokens for a user. Creates persistent user if email provided, reuses existing user."""
        # Validate username is not a user_id format to prevent confusion
        if username.startswith('user_') and len(username) > 10:
            # This looks like a user_id, try to find user by user_id instead
            db_user = self.user_repo.find_by_user_id(username)
            if db_user:
                # Found user by user_id, use their actual username
                username = db_user.username
                email = email or db_user.email
            else:
                # Not found, this is invalid - user_id should not be used as username
                raise ValueError("Invalid username format. Cannot use user_id as username.")
        
        # Get or create persistent user - this will find existing by email or username
        db_user = self.user_repo.create_or_get(username, role.value, email=email)
        
        # Create in-memory user for AuthService compatibility
        auth_user = AuthUser(db_user.user_id, db_user.username, Role(db_user.role))
        
        # Generate access token
        if self._jwt:
            token = self._jwt.encode({
                'sub': db_user.user_id,
                'username': db_user.username,
                'role': db_user.role,
            }, self.secret, algorithm='HS256')
        else:
            token = f"token_{db_user.user_id}_{datetime.utcnow().timestamp()}"
        
        # Generate refresh token
        if self._jwt:
            refresh = self._jwt.encode({
                'sub': db_user.user_id,
                'username': db_user.username,
                'role': db_user.role,
                'type': 'refresh',
                'exp': datetime.utcnow() + timedelta(days=7)
            }, self.secret, algorithm='HS256')
        else:
            refresh = f"refresh_{db_user.user_id}_{datetime.utcnow().timestamp()}"
        
        # Persist tokens
        self.repo.save(db_user.user_id, token, 'access', expires_at=datetime.utcnow() + timedelta(hours=12))
        self.repo.save(db_user.user_id, refresh, 'refresh', expires_at=datetime.utcnow() + timedelta(days=7))
        
        # Also add to in-memory AuthService for backward compatibility
        auth_service = self.auth
        auth_service.tokens[token] = auth_user
        
        return TokenPair(token, refresh, db_user.user_id, db_user.role, db_user.username)

    def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Refresh access token using refresh token. Maintains same user_id."""
        # Validate refresh token in database
        token_rec = self.repo.get(refresh_token)
        if not token_rec or token_rec.token_type != 'refresh':
            raise ValueError("Invalid refresh token")
        if token_rec.expires_at and datetime.utcnow() > token_rec.expires_at:
            raise ValueError("Refresh token expired")
        
        # Get user_id from token record
        user_id = token_rec.user_id
        
        # Verify JWT if available
        if self._jwt:
            try:
                payload = self._jwt.decode(refresh_token, self.secret, algorithms=['HS256'])
                # Ensure user_id matches
                if payload.get('sub') != user_id:
                    raise ValueError("Token user_id mismatch")
                user_id = payload.get('sub')
            except Exception:
                raise ValueError("Invalid refresh token format")
        
        # Get persistent user - this ensures we use the same user record
        db_user = self.user_repo.find_by_user_id(user_id)
        if not db_user:
            raise ValueError("User not found")
        
        # Generate new access token with same user_id and attributes
        if self._jwt:
            new_access = self._jwt.encode({
                'sub': db_user.user_id,
                'username': db_user.username,
                'role': db_user.role,
            }, self.secret, algorithm='HS256')
        else:
            new_access = f"token_{db_user.user_id}_{datetime.utcnow().timestamp()}"
        
        # Optionally generate new refresh token (or reuse old one)
        # Here we generate a new one for security
        if self._jwt:
            new_refresh = self._jwt.encode({
                'sub': db_user.user_id,
                'username': db_user.username,
                'role': db_user.role,
                'type': 'refresh',
                'exp': datetime.utcnow() + timedelta(days=7)
            }, self.secret, algorithm='HS256')
        else:
            new_refresh = f"refresh_{db_user.user_id}_{datetime.utcnow().timestamp()}"
        
        # Revoke old refresh token
        self.repo.revoke(refresh_token)
        
        # Persist new tokens with same user_id
        self.repo.save(db_user.user_id, new_access, 'access', expires_at=datetime.utcnow() + timedelta(hours=12))
        self.repo.save(db_user.user_id, new_refresh, 'refresh', expires_at=datetime.utcnow() + timedelta(days=7))
        
        # Add to in-memory AuthService
        auth_service = self.auth
        auth_user = AuthUser(db_user.user_id, db_user.username, Role(db_user.role))
        auth_service.tokens[new_access] = auth_user
        
        # Return TokenPair with username for frontend
        return TokenPair(new_access, new_refresh, db_user.user_id, db_user.role, db_user.username)


app_auth_service = AppAuthService()


