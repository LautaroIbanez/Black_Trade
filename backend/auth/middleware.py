"""Authentication middleware for request auditing."""
import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.auth.permissions import get_auth_service, User

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and request auditing."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with authentication."""
        # Skip auth for health checks and public endpoints
        if request.url.path in ["/health", "/api/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        
        # Track user for audit logging
        user: Optional[User] = None
        if auth_header:
            try:
                token = auth_header.replace("Bearer ", "")
                auth_service = get_auth_service()
                user = auth_service.authenticate(token)
            except Exception as e:
                logger.debug(f"Authentication error: {e}")
        
        # Log request (without sensitive data)
        logger.info(
            f"{request.method} {request.url.path} - "
            f"User: {user.username if user else 'anonymous'}"
        )
        
        # Continue request
        response = await call_next(request)
        
        return response

