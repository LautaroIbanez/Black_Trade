# Authentication & Authorization Guide

## Overview

Black Trade uses JWT-based authentication with KYC verification, persistent token storage, and role-based access control (RBAC).

## Architecture

### Components

1. **AuthService** (`backend/auth/permissions.py`): Core authentication and authorization service
2. **AppAuthService** (`backend/services/auth_service.py`): High-level wrapper that issues JWT tokens and persists them
3. **KYCService** (`backend/compliance/kyc_aml.py`): Know Your Customer verification service
4. **UserTokensRepository**: Persists access and refresh tokens with expiration

### Flow

```
1. User Registration
   POST /api/auth/register
   → Creates user account (not verified)
   → Issues access + refresh tokens
   → Returns {access_token, refresh_token, user_id, role}
   
2. KYC Verification
   POST /api/auth/verify
   → Verifies user identity with documents
   → Marks user as verified in database
   
3. Accessing Protected Resources
   GET /api/recommendations/live
   GET /api/risk/*
   → Requires Bearer token in Authorization header
   → Verifies token and checks permissions
   → Enforces KYC verification for sensitive endpoints
   
4. Token Refresh
   POST /api/auth/refresh
   → Uses refresh token to get new access token
   → Refresh tokens expire after 7 days
```

## User Roles & Permissions

### Roles

- **VIEWER**: Read-only access to recommendations, risk metrics, execution
- **TRADER**: Can create orders, cancel orders, read everything
- **RISK_MANAGER**: Can manage risk limits, read everything
- **ADMIN**: Full system access

### Permission Mapping

```python
ROLE_PERMISSIONS = {
    Role.VIEWER: {
        READ_RECOMMENDATIONS,
        READ_RISK_METRICS,
        READ_EXECUTION,
        READ_METRICS,
    },
    Role.TRADER: {
        READ_RECOMMENDATIONS,
        READ_RISK_METRICS,
        READ_EXECUTION,
        READ_JOURNAL,
        READ_METRICS,
        CREATE_ORDERS,
        CANCEL_ORDERS,
    },
    Role.RISK_MANAGER: {
        READ_RECOMMENDATIONS,
        READ_RISK_METRICS,
        READ_EXECUTION,
        READ_JOURNAL,
        READ_METRICS,
        WRITE_RISK_LIMITS,
        MANUAL_INTERVENTION,
    },
    Role.ADMIN: {All permissions},
}
```

## Endpoints

### `/api/auth/register`

Creates a new user account and issues tokens.

**Request**:
```json
{
  "username": "trader1",
  "email": "trader@example.com",
  "country": "AR",
  "role": "viewer"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": "user_0",
  "role": "viewer"
}
```

### `/api/auth/login`

Logs in an existing user and issues new tokens.

**Request**:
```json
{
  "username": "trader1",
  "role": "viewer"
}
```

**Response**: Same as register

### `/api/auth/verify`

Verifies user's KYC status with documents.

**Request**:
```json
{
  "user_id": "user_0",
  "document_type": "passport",
  "document_number": "ABC123"
}
```

**Response**:
```json
{
  "verified": true
}
```

### `/api/auth/kyc-status`

Checks current KYC verification status.

**Request**:
```json
{
  "user_id": "user_0"
}
```

**Response**:
```json
{
  "verified": true,
  "status": "verified",
  "verification_date": "2025-11-03T14:00:00"
}
```

### `/api/auth/refresh`

Refreshes access token using refresh token.

**Request**:
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": "user_0",
  "role": "viewer"
}
```

## Token Storage

Tokens are persisted in `user_tokens` table:

- **access_token**: Expires after 12 hours
- **refresh_token**: Expires after 7 days

Both tokens include expiration timestamps for validation.

### Token Revocation

The repository supports:
- `revoke(token)`: Revoke a specific token
- `revoke_all_for_user(user_id)`: Revoke all tokens for a user
- `is_expired(token)`: Check if a token has expired

## Protected Endpoints

All protected endpoints require:
1. `Authorization: Bearer <access_token>` header
2. Valid, non-expired token
3. KYC verification (for sensitive resources)

### KYC-Gated Endpoints

- `/api/recommendations/live`: Get live trading recommendations
- `/api/risk/*`: Risk metrics and management
- `/api/recommendation-tracking/*`: Track recommendation outcomes

### Permission-Gated Endpoints

- `CREATE_ORDERS`: POST `/api/execution/orders`
- `WRITE_RISK_LIMITS`: POST `/api/risk/limits`
- `ADMIN_*`: Various admin operations

## Frontend Integration

### Authentication Service

`frontend/src/services/auth.ts` provides:

- `setSession(token, userId, role, refreshToken, username)`: Store session
- `refreshAccessToken()`: Refresh expired access token
- `ensureSession()`: Ensure valid session exists
- `authHeader()`: Get Authorization header

### AuthGate Component

`frontend/src/components/AuthGate.tsx`:
- Blocks unauthenticated users
- Shows login/register forms
- Handles KYC verification flow

### Using in Hooks

```typescript
import { useRecommendations } from '../hooks/useRecommendations'

// Automatically handles auth and KYC checks
const { items, loading, error, kycBlocked } = useRecommendations('balanced')
```

## Environment Variables

```bash
# JWT Configuration
JWT_SECRET=your-secret-key-here

# Database (for token storage)
DATABASE_URL=postgresql://user:password@localhost:5432/black_trade

# KYC Provider (future integration)
KYC_PROVIDER_API_KEY=...
```

## Security Best Practices

1. **Rotate JWT_SECRET regularly** in production
2. **Use HTTPS** for all authentication endpoints
3. **Implement rate limiting** on auth endpoints
4. **Log authentication failures** for monitoring
5. **Validate token expiration** server-side
6. **Store refresh tokens securely** (HTTP-only cookies in production)

## Testing

See `tests/api/test_auth_flow.py` for integration tests covering:
- Registration flow
- KYC verification
- Token refresh
- Protected endpoint access

## Dependency Injection for Permissions

### Correct Usage Pattern

When adding authentication to FastAPI endpoints, **always use the dependency functions** from `backend/api/dependencies.py` instead of creating new `AuthService()` instances.

#### ✅ CORRECT: Using Pre-built Dependencies

```python
from fastapi import Depends
from backend.api.dependencies import require_recommendation_access, require_risk_metrics_access
from backend.auth.permissions import User

@router.get("/recommendations")
async def get_recommendations(user: User = Depends(require_recommendation_access)):
    # user is a User object with user_id, username, role, etc.
    return {"user_id": user.user_id, "items": [...]}
```

#### ❌ INCORRECT: Creating New AuthService Instances

```python
# DON'T DO THIS - Creates new instance and returns function instead of User
from backend.auth.permissions import AuthService, Permission

@router.get("/recommendations")
async def get_recommendations(user=Depends(lambda: AuthService().require_permission(Permission.READ_RECOMMENDATIONS))):
    # This will fail with AttributeError - user is a function, not User object
    return {"user_id": user.user_id}  # ❌ AttributeError!
```

### Available Dependencies

The following pre-built dependencies are available in `backend/api/dependencies.py`:

- `require_recommendation_access`: Requires `READ_RECOMMENDATIONS` permission
- `require_risk_metrics_access`: Requires `READ_RISK_METRICS` permission
- `require_create_orders_access`: Requires `CREATE_ORDERS` permission
- `require_cancel_orders_access`: Requires `CANCEL_ORDERS` permission
- `require_write_risk_limits_access`: Requires `WRITE_RISK_LIMITS` permission
- `get_current_user`: Returns authenticated user without permission check

### Creating New Permission Dependencies

If you need a dependency for a permission not yet covered, use the factory pattern:

```python
from backend.api.dependencies import _make_permission_dependency
from backend.auth.permissions import Permission

# Create a new dependency
require_my_custom_permission = _make_permission_dependency(Permission.MY_CUSTOM_PERMISSION)

# Use it in your endpoint
@router.get("/my-endpoint")
async def my_endpoint(user: User = Depends(require_my_custom_permission)):
    return {"user_id": user.user_id}
```

### Why This Matters

1. **Singleton Pattern**: `AuthService` must be a singleton across the application to ensure consistent token storage and user management.

2. **Type Safety**: Using the proper dependencies ensures FastAPI correctly injects the `User` object, enabling type checking and IDE autocomplete.

3. **Consistency**: All endpoints use the same `AuthService` instance initialized at startup via `init_auth_service()`.

4. **Testing**: The dependency injection pattern makes it easy to mock `AuthService` in tests.

### Internal Implementation

The dependencies use `get_auth_service()` to obtain the singleton instance:

```python
async def require_permission(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_service: AuthService = Depends(get_auth_service),  # ← Singleton getter
) -> User:
    user = auth_service.authenticate(credentials.credentials)
    if not user or not user.has_permission(permission):
        raise HTTPException(...)
    return user
```

This ensures that all authentication logic uses the same `AuthService` instance initialized during application startup.

