# Frontend Authentication Guide

## Overview

The frontend uses React Context + localStorage to manage JWT authentication with automatic token refresh, KYC verification gating, and protected API calls.

## Architecture

### Components

1. **AuthContext** (`frontend/src/context/AuthContext.tsx`): Global auth state provider
2. **AuthGate** (`frontend/src/components/AuthGate.tsx`): KYC verification gate
3. **Auth Service** (`frontend/src/services/auth.ts`): Token storage and refresh utilities
4. **Hooks**: `useRecommendations`, `useRiskData` with built-in auth handling

### Flow

```
┌─────────────────────────┐
│   User Opens App        │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   AuthProvider Loads    │
│   Check localStorage    │
└────────────┬────────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
┌─────────┐    ┌──────────────┐
│ No Token│    │ Token Found  │
└────┬────┘    └──────┬───────┘
     │                │
     ▼                ▼
┌─────────────────────────┐
│  AuthGate Shows Login   │
│  User Logs In/Registers │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Store Tokens in        │
│  localStorage           │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Check KYC Status       │
└────────────┬────────────┘
     ┌───────┴───────┐
     │               │
     ▼               ▼
┌─────────┐    ┌──────────────┐
│Unverified│    │   Verified   │
└────┬────┘    └──────┬───────┘
     │                │
     ▼                ▼
┌─────────────────────────┐
│  Show KYC Form         │
│  User Submits Docs      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Grant Access to        │
│  Protected Resources    │
└─────────────────────────┘
```

## Usage

### Setting Up AuthProvider

Wrap your app with `AuthProvider`:

```tsx
import { AuthProvider } from './context/AuthContext'

function App() {
  return (
    <AuthProvider>
      <YourApp />
    </AuthProvider>
  )
}
```

### Using Auth State

Access auth state in any component:

```tsx
import { useAuth } from '../context/AuthContext'

function MyComponent() {
  const { isAuthenticated, token, userId, isKYCVerified, logout } = useAuth()
  
  if (!isAuthenticated) {
    return <div>Please log in</div>
  }
  
  if (!isKYCVerified) {
    return <div>KYC verification required</div>
  }
  
  return <div>Welcome {userId}</div>
}
```

### Protected API Calls

Use `retryProtectedCall` for automatic token refresh:

```tsx
const { retryProtectedCall } = useAuth()

const loadData = async () => {
  try {
    const result = await retryProtectedCall(() => fetch('/api/protected'))
    // Handle result
  } catch (error) {
    // Handle error (already retried)
  }
}
```

### Hooks with Built-in Auth

Use `useRecommendations` and `useRiskData` hooks that handle auth automatically:

```tsx
import { useRecommendations } from '../hooks/useRecommendations'
import { useRiskData } from '../hooks/useRiskData'

function Dashboard() {
  const { items, loading, error, kycBlocked } = useRecommendations('balanced')
  const { data, loading: riskLoading } = useRiskData()
  
  if (kycBlocked) {
    return <div>Please complete KYC verification</div>
  }
  
  return <div>{/* Render data */}</div>
}
```

## Token Management

### Storage

Tokens are stored in `localStorage`:

- `bt_auth_token`: Access token (expires after 12 hours)
- `bt_refresh_token`: Refresh token (expires after 7 days)
- `bt_user_id`: User identifier
- `bt_user_role`: User role (viewer/trader/risk_manager/admin)
- `bt_username`: Username

### Refresh Flow

```typescript
1. Access token expires (401 response)
   ↓
2. Hooks detect 401 error
   ↓
3. Call refreshAccessToken()
   ↓
4. Send refresh_token to backend
   ↓
5. Receive new access_token + refresh_token
   ↓
6. Update localStorage
   ↓
7. Retry original request with new token
```

### Manual Refresh

```typescript
import { refreshAccessToken } from '../services/auth'

// Returns true if refresh successful, false otherwise
const refreshed = await refreshAccessToken()
```

## KYC Verification Flow

### Check KYC Status

```typescript
import { checkKYCStatus } from '../services/api'

const status = await checkKYCStatus(userId)
// Returns: { verified: boolean, status: string, verification_date: string | null }
```

### Verify KYC

```typescript
import { verifyKYC } from '../services/api'

await verifyKYC({
  user_id: userId,
  document_type: 'passport',
  document_number: 'ABC123'
})
```

### UI Integration

`AuthGate` component automatically handles KYC flow:

```tsx
<AuthGate>
  <YourProtectedContent />
</AuthGate>
```

States:
- **No token**: Shows login/register form
- **Token, no KYC**: Shows KYC verification form
- **Token + KYC**: Shows protected content

## Error Handling

### 401 Unauthorized

Automatically triggers token refresh:

```typescript
// In hooks or components using retryProtectedCall
try {
  const data = await retryProtectedCall(() => fetch('/api/data'))
} catch (error) {
  // Already retried once with refresh
  // Handle persistent error
}
```

### 403 Forbidden (KYC)

Some endpoints require KYC verification:

```typescript
const { items, kycBlocked } = useRecommendations('balanced')

if (kycBlocked) {
  return <KYCRequiredBanner />
}
```

### Session Expired

If refresh token expires, user must log in again:

```typescript
const { logout } = useAuth()

// After failed refresh
logout()
// Redirect to login
```

## Best Practices

1. **Always use `retryProtectedCall`** for protected API calls
2. **Check `kycBlocked`** state before rendering sensitive data
3. **Use hooks** (`useRecommendations`, `useRiskData`) instead of manual API calls when possible
4. **Don't store sensitive data** in localStorage (tokens are ok for this app)
5. **Handle loading states** when checking auth
6. **Logout on invalid token** to force re-authentication

## Testing

### Unit Tests

```typescript
import { renderHook, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../context/AuthContext'

test('refreshes token on 401', async () => {
  const wrapper = ({ children }) => <AuthProvider>{children}</AuthProvider>
  const { result } = renderHook(() => useAuth(), { wrapper })
  
  // Test token refresh
  const refreshed = await result.current.retryProtectedCall(() => {
    throw { status: 401 }
  })
})
```

### E2E Tests

See `docs/qa/frontend.md` for complete E2E scenarios.

