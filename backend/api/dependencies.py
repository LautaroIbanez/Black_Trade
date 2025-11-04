"""FastAPI dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.auth.permissions import (
    AuthService,
    Permission,
    Role,
    User,
    get_auth_service,
)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency to get the current authenticated user."""
    user = auth_service.authenticate(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _make_permission_dependency(permission: Permission):
    """Factory that creates a dependency function for a specific permission."""
    async def require_permission(
        credentials: HTTPAuthorizationCredentials = Security(security),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User:
        """Dependency to require a specific permission."""
        user = auth_service.authenticate(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Required: {permission.value}",
            )
        return user
    return require_permission


# Pre-created dependencies for common permissions
require_recommendation_access = _make_permission_dependency(Permission.READ_RECOMMENDATIONS)
require_risk_metrics_access = _make_permission_dependency(Permission.READ_RISK_METRICS)
require_create_orders_access = _make_permission_dependency(Permission.CREATE_ORDERS)
require_cancel_orders_access = _make_permission_dependency(Permission.CANCEL_ORDERS)
require_write_risk_limits_access = _make_permission_dependency(Permission.WRITE_RISK_LIMITS)
