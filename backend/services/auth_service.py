"""High-level authentication service issuing JWT access/refresh and persisting them."""
import os
from datetime import datetime, timedelta
from typing import Tuple

from backend.auth.permissions import AuthService, Role, get_auth_service
from backend.repositories.user_tokens_repository import UserTokensRepository


class TokenPair:
    def __init__(self, access_token: str, refresh_token: str, user_id: str, role: str):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.role = role


class AppAuthService:
    def __init__(self):
        self.repo = UserTokensRepository()
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

    def issue_tokens(self, username: str, role: Role) -> TokenPair:
        auth_service = self.auth
        token, user = auth_service.create_user(username, role)
        if self._jwt:
            refresh = self._jwt.encode({'sub': user.user_id, 'username': user.username, 'type': 'refresh', 'exp': datetime.utcnow() + timedelta(days=7)}, self.secret, algorithm='HS256')
        else:
            refresh = f"refresh_{user.user_id}_{datetime.utcnow().timestamp()}"
        self.repo.save(user.user_id, token, 'access', expires_at=datetime.utcnow() + timedelta(hours=12))
        self.repo.save(user.user_id, refresh, 'refresh', expires_at=datetime.utcnow() + timedelta(days=7))
        return TokenPair(token, refresh, user.user_id, user.role.value)


app_auth_service = AppAuthService()


