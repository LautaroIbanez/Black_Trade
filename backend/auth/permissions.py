"""Permission and role-based access control."""
import logging
from typing import List, Optional, Dict, Set
import os
from enum import Enum
from functools import wraps
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    # Read permissions
    READ_RECOMMENDATIONS = "read:recommendations"
    READ_RISK_METRICS = "read:risk_metrics"
    READ_EXECUTION = "read:execution"
    READ_JOURNAL = "read:journal"
    READ_METRICS = "read:metrics"
    
    # Write permissions
    WRITE_RISK_LIMITS = "write:risk_limits"
    CREATE_ORDERS = "write:orders"
    CANCEL_ORDERS = "write:cancel_orders"
    MANUAL_INTERVENTION = "write:manual_intervention"
    
    # Admin permissions
    ADMIN_USERS = "admin:users"
    ADMIN_CONFIG = "admin:config"
    ADMIN_AUDIT = "admin:audit"


class Role(str, Enum):
    """User roles."""
    VIEWER = "viewer"  # Read-only access
    TRADER = "trader"  # Can create orders, read everything
    RISK_MANAGER = "risk_manager"  # Can manage risk limits, read everything
    ADMIN = "admin"  # Full access


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_RECOMMENDATIONS,
        Permission.READ_RISK_METRICS,
        Permission.READ_EXECUTION,
        Permission.READ_METRICS,
    },
    Role.TRADER: {
        Permission.READ_RECOMMENDATIONS,
        Permission.READ_RISK_METRICS,
        Permission.READ_EXECUTION,
        Permission.READ_JOURNAL,
        Permission.READ_METRICS,
        Permission.CREATE_ORDERS,
        Permission.CANCEL_ORDERS,
    },
    Role.RISK_MANAGER: {
        Permission.READ_RECOMMENDATIONS,
        Permission.READ_RISK_METRICS,
        Permission.READ_EXECUTION,
        Permission.READ_JOURNAL,
        Permission.READ_METRICS,
        Permission.WRITE_RISK_LIMITS,
        Permission.MANUAL_INTERVENTION,
    },
    Role.ADMIN: set(Permission),  # All permissions
}


class User:
    """User model."""
    
    def __init__(self, user_id: str, username: str, role: Role, permissions: Optional[Set[Permission]] = None):
        """
        Initialize user.
        
        Args:
            user_id: Unique user ID
            username: Username
            role: User role
            permissions: Additional permissions (defaults to role permissions)
        """
        self.user_id = user_id
        self.username = username
        self.role = role
        self.permissions = permissions or ROLE_PERMISSIONS.get(role, set())
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission."""
        return permission in self.permissions


# Security scheme
security = HTTPBearer()


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        """Initialize auth service."""
        # In production, use proper authentication (JWT, OAuth, etc.)
        self.tokens: Dict[str, User] = {}
        self.logger = logging.getLogger(__name__)
        # Optional JWT support
        self.jwt_secret = os.getenv('JWT_SECRET')
        try:
            import jwt  # type: ignore
            self._jwt = jwt
        except Exception:
            self._jwt = None
    
    def create_user(self, username: str, role: Role) -> tuple[str, User]:
        """
        Create user and generate token.
        
        Args:
            username: Username
            role: User role
            
        Returns:
            Tuple of (token, user)
        """
        user_id = f"user_{len(self.tokens)}"
        user = User(user_id, username, role)
        # Prefer JWT if available
        if self._jwt and self.jwt_secret:
            token = self._jwt.encode({
                'sub': user_id,
                'username': username,
                'role': role.value,
            }, self.jwt_secret, algorithm='HS256')
            # Also map for fast lookup
            self.tokens[token] = user
            return token, user
        else:
            token = f"token_{user_id}"
            self.tokens[token] = user
            return token, user
    
    def authenticate(self, token: str) -> Optional[User]:
        """
        Authenticate user by token.
        
        Args:
            token: Authentication token
            
        Returns:
            User if authenticated, None otherwise
        """
        user = self.tokens.get(token)
        if user:
            return user
        # Try decode JWT
        if self._jwt and self.jwt_secret:
            try:
                payload = self._jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
                uid = payload.get('sub')
                username = payload.get('username')
                role = Role(payload.get('role', 'viewer'))
                # Cache mapping
                u = User(uid, username, role)
                self.tokens[token] = u
                return u
            except Exception:
                return None
        return None
    
    def require_permission(self, permission: Permission):
        """
        Dependency to require specific permission.
        
        Args:
            permission: Required permission
        """
        async def permission_checker(
            credentials: HTTPAuthorizationCredentials = Security(security),
            auth_service: "AuthService" = Depends(lambda: get_auth_service()),
        ) -> User:
            user = auth_service.authenticate(credentials.credentials)
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied. Required: {permission.value}",
                )
            
            return user
        
        return permission_checker
    
    def require_role(self, role: Role):
        """
        Dependency to require specific role.
        
        Args:
            role: Required role
        """
        async def role_checker(
            credentials: HTTPAuthorizationCredentials = Security(security),
            auth_service: "AuthService" = Depends(lambda: get_auth_service()),
        ) -> User:
            user = auth_service.authenticate(credentials.credentials)
            if not user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            if user.role != role and user.role != Role.ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail=f"Role denied. Required: {role.value}",
                )
            
            return user
        
        return role_checker
    
    def audit_log(self, user: User, action: str, resource: str, details: Optional[Dict] = None):
        """Log audit event."""
        from backend.logging.journal import transaction_journal, JournalEntryType
        
        transaction_journal.log(
            JournalEntryType.MANUAL_INTERVENTION,
            details={
                'action': action,
                'resource': resource,
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role.value,
                **(details or {}),
            },
            user=user.username,
        )
        
        self.logger.info(f"Audit: {user.username} ({user.role.value}) - {action} on {resource}")


# Global auth service instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def init_auth_service() -> AuthService:
    """Initialize auth service with default users."""
    global _auth_service
    auth_service = AuthService()
    
    # Create default users (in production, load from database)
    auth_service.create_user("viewer", Role.VIEWER)
    auth_service.create_user("trader", Role.TRADER)
    auth_service.create_user("risk_manager", Role.RISK_MANAGER)
    auth_service.create_user("admin", Role.ADMIN)
    
    _auth_service = auth_service
    return auth_service

