"""Security configuration and utilities."""
import os
import hashlib
import secrets
from typing import Optional, Dict
from functools import wraps
from datetime import datetime, timedelta

import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class SecretManager:
    """Manages secrets securely."""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None, required: bool = True) -> Optional[str]:
        """
        Get secret from environment or secret store.
        
        In production, integrate with:
        - AWS Secrets Manager
        - HashiCorp Vault
        - Azure Key Vault
        - Google Secret Manager
        
        Args:
            key: Secret key
            default: Default value if not found
            required: If True, raise error if secret not found
            
        Returns:
            Secret value
        """
        value = os.getenv(key, default)
        
        if required and not value:
            raise ValueError(f"Required secret '{key}' not found")
        
        return value
    
    @staticmethod
    def hash_secret(secret: str) -> str:
        """Hash a secret using SHA-256."""
        return hashlib.sha256(secret.encode()).hexdigest()
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        """Initialize rate limiter."""
        self.requests: Dict[str, list] = {}
    
    def is_allowed(
        self,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=window_seconds)
        
        # Get requests in current window
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check limit
        request_count = len(self.requests[identifier])
        
        if request_count >= max_requests:
            return False, 0
        
        # Add current request
        self.requests[identifier].append(now)
        
        return True, max_requests - request_count - 1


class SecurityHeaders:
    """Security headers middleware."""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers to add to responses."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }


class InputValidator:
    """Input validation utilities."""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.
        
        Args:
            value: Input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]
        
        return value.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_alphanumeric(value: str, min_length: int = 1, max_length: int = 100) -> bool:
        """Validate alphanumeric string."""
        import re
        pattern = f'^[a-zA-Z0-9_]{{{min_length},{max_length}}}$'
        return bool(re.match(pattern, value))


# Global instances
_secret_manager = SecretManager()
_rate_limiter = RateLimiter()


def get_secret_manager() -> SecretManager:
    """Get global secret manager instance."""
    return _secret_manager


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get client identifier (IP address)
            client_ip = request.client.host if request.client else "unknown"
            
            # Check rate limit
            is_allowed, remaining = get_rate_limiter().is_allowed(
                identifier=client_ip,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            
            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
                    headers={"Retry-After": str(window_seconds)},
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator

