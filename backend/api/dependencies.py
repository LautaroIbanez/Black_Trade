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
from backend.repositories.user_repository import UserRepository
from backend.repositories.kyc_repository import KYCRepository

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


async def get_verified_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency to get the current authenticated and KYC-verified user."""
    user = auth_service.authenticate(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify user exists in persistent store
    user_repo = UserRepository()
    db_user = user_repo.find_by_user_id(user.user_id)
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found in persistent store")
    
    # Verify KYC status from database (not from token)
    kyc_repo = KYCRepository()
    if not kyc_repo.is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    
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
        
        # Verify user exists in persistent store
        user_repo = UserRepository()
        db_user = user_repo.find_by_user_id(user.user_id)
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found in persistent store")
        
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Required: {permission.value}",
            )
        return user
    return require_permission


def _make_kyc_required_dependency(permission: Permission):
    """Factory that creates a dependency function requiring both permission and KYC verification."""
    async def require_permission_and_kyc(
        credentials: HTTPAuthorizationCredentials = Security(security),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User:
        """Dependency to require a specific permission AND KYC verification."""
        user = auth_service.authenticate(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Verify user exists in persistent store
        user_repo = UserRepository()
        db_user = user_repo.find_by_user_id(user.user_id)
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found in persistent store")
        
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Required: {permission.value}",
            )
        
        # Verify KYC status from database (not from token)
        kyc_repo = KYCRepository()
        if not kyc_repo.is_verified(user.user_id):
            raise HTTPException(status_code=403, detail="KYC verification required")
        
        return user
    return require_permission_and_kyc


# Pre-created dependencies for common permissions
require_recommendation_access = _make_permission_dependency(Permission.READ_RECOMMENDATIONS)
require_risk_metrics_access = _make_permission_dependency(Permission.READ_RISK_METRICS)
require_create_orders_access = _make_permission_dependency(Permission.CREATE_ORDERS)
require_cancel_orders_access = _make_permission_dependency(Permission.CANCEL_ORDERS)
require_write_risk_limits_access = _make_permission_dependency(Permission.WRITE_RISK_LIMITS)

# Pre-created dependencies requiring KYC verification
require_recommendation_access_with_kyc = _make_kyc_required_dependency(Permission.READ_RECOMMENDATIONS)
require_risk_metrics_access_with_kyc = _make_kyc_required_dependency(Permission.READ_RISK_METRICS)
require_create_orders_access_with_kyc = _make_kyc_required_dependency(Permission.CREATE_ORDERS)
