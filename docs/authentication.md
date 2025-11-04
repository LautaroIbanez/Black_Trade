# Authentication & Authorization Guide

## Overview

Black Trade uses JWT-based authentication with KYC verification, persistent token storage, and role-based access control (RBAC).

## Architecture

### Components

1. **AuthService** (`backend/auth/permissions.py`): Core authentication and authorization service
2. **AppAuthService** (`backend/services/auth_service.py`): High-level wrapper that issues JWT tokens and persists them
3. **UserRepository** (`backend/repositories/user_repository.py`): Manages persistent user identity in database
4. **KYCService** (`backend/compliance/kyc_aml.py`): Know Your Customer verification service
5. **UserTokensRepository**: Persists access and refresh tokens with expiration

### User Identity Persistence

**Critical**: All users are persisted in the `users` database table with a stable `user_id` that **never changes** throughout the user's lifecycle. This ensures:

1. **Stable Identity**: The `user_id` remains constant across login sessions, token refreshes, and API calls
2. **KYC Persistence**: KYC verification status is tied to the persistent `user_id`, so it persists across token refreshes
3. **Email-based Deduplication**: When registering with an existing email, the system reuses the existing user record and `user_id`

#### User Creation and Lookup

- **Registration** (`/api/auth/register`): 
  - If email is provided and exists in database → returns existing user's `user_id`
  - If email is new → creates new persistent user with unique `user_id`
  - The `user_id` format is `user_<12-char-hex>` (e.g., `user_a1b2c3d4e5f6`)

- **Login** (`/api/auth/login`):
  - Creates a new persistent user if username doesn't exist
  - **Note**: For proper identity consolidation, use registration with email

- **Token Refresh** (`/api/auth/refresh`):
  - **Always maintains the same `user_id`** from the refresh token
  - Generates new access and refresh tokens but preserves user identity
  - KYC verification and all user data remain accessible

#### Why This Matters

The authentication and permission services depend on an **immutable `user_id`**. Without persistence:
- Token refresh would create new `user_id`, breaking KYC verification
- User data (recommendations, risk metrics) would be lost between sessions
- Permission checks would fail due to missing user context

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
   → Validates refresh token from database
   → Maintains same user_id from token record
   → Generates new access + refresh tokens
   → Old refresh token is revoked
   → KYC status and user data remain accessible
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

Refreshes access token using refresh token. **Maintains the same `user_id`** from the original token.

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
  "user_id": "user_a1b2c3d4e5f6",
  "role": "viewer"
}
```

**Important**: 
- The `user_id` in the response is **always the same** as the `user_id` from the original registration/login
- The old refresh token is invalidated after refresh
- KYC verification status persists and remains accessible with the new tokens

## User and Token Storage

### User Persistence

Users are stored in the `users` table with the following schema:
- **user_id** (VARCHAR, UNIQUE): Immutable identifier (format: `user_<12-char-hex>`)
- **username** (VARCHAR): Display name
- **email** (VARCHAR, UNIQUE): Email address (used for identity consolidation)
- **role** (VARCHAR): User role (viewer/trader/risk_manager/admin)
- **created_at**, **updated_at**: Timestamps

The `user_id` is **never changed** after creation, ensuring:
- Stable identity across all authentication flows
- KYC verification persistence
- Data integrity for recommendations, risk metrics, and user tracking

### Token Storage

Tokens are persisted in `user_tokens` table:

- **user_id** (VARCHAR): References the persistent user
- **token** (VARCHAR, UNIQUE): The JWT or token string
- **token_type** (VARCHAR): 'access' or 'refresh'
- **access_token**: Expires after 12 hours
- **refresh_token**: Expires after 7 days

Both tokens include expiration timestamps for validation. When a refresh token is used, the old refresh token is revoked and a new pair is issued, maintaining the same `user_id`.

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
- Registration flow with persistent user creation
- User identity consolidation by email
- KYC verification persistence
- Token refresh maintaining same `user_id`
- KYC status persistence across token refresh
- Complete flow: login → refresh → access protected endpoints
- Multiple token refreshes maintaining identity
- Refresh token invalidation after use

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

