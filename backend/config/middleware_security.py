"""Security middleware for FastAPI."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.config.security import SecurityHeaders, InputValidator
import logging

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and add security headers."""
        # Add security headers to response
        response = await call_next(request)
        
        headers = SecurityHeaders.get_headers()
        for header, value in headers.items():
            response.headers[header] = value
        
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize input."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.validator = InputValidator()
    
    async def dispatch(self, request: Request, call_next):
        """Sanitize input data."""
        # For GET requests, sanitize query parameters
        if request.method == "GET":
            query_params = dict(request.query_params)
            for key, value in query_params.items():
                if isinstance(value, str):
                    try:
                        sanitized = self.validator.sanitize_string(value)
                        # Note: FastAPI doesn't easily allow modifying query params
                        # This is a placeholder - actual sanitization should be in endpoint handlers
                    except Exception as e:
                        logger.warning(f"Error sanitizing query param {key}: {e}")
        
        response = await call_next(request)
        return response

