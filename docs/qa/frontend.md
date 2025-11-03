# Frontend QA: Authentication & Protected Data Flow

## Goal

Validate complete authentication flow from login to accessing protected resources with KYC verification and token management.

## Preconditions

- Backend API running with database initialized
- `JWT_SECRET` environment variable set
- Risk engine and ingestion schedulers running
- Frontend built with `npm run build` or served via `npm run dev`

## E2E Scenarios

### Scenario 1: New User Registration → KYC → Access

**Steps:**

1. Open application in browser
2. **AuthGate appears** - Verify login/register forms are displayed
3. **Register new user**:
   - Enter username: `testuser1`
   - Enter email: `test1@example.com`
   - Select country: `AR`
   - Click "Registrar"
4. **Verify registration**:
   - Alert appears: "Registro exitoso. Verifique KYC para acceder a datos protegidos."
   - KYC verification form appears
   - Check `localStorage` contains: `bt_auth_token`, `bt_refresh_token`, `bt_user_id`, `bt_username`
5. **Complete KYC verification**:
   - Select document type: `Passport`
   - Enter document: `TEST123`
   - Click "Verificar"
6. **Verify KYC completion**:
   - Alert: "KYC verificado exitosamente"
   - Dashboard content appears (not blocked by AuthGate)
7. **Access protected resources**:
   - Recommendations section loads items (or empty state with 200 status)
   - Risk overview displays metrics without 403 error
   - WebSocket connection establishes

**Expected Results:**
- No 401/403 errors after KYC verification
- Dashboard displays live data
- Real-time WebSocket updates appear

### Scenario 2: Existing User Login → Token Refresh

**Steps:**

1. Clear browser `localStorage` (or use incognito)
2. Open application
3. **Login with existing user**:
   - Enter username: `testuser1`
   - Click "Login"
4. **Verify dashboard loads** (assuming KYC was verified previously)
5. **Simulate token expiration** (optional, via browser console):
   ```javascript
   // Manually remove access token to simulate expiration
   localStorage.removeItem('bt_auth_token')
   ```
6. **Trigger API call** - Wait for auto-refresh to execute
7. **Verify token refresh**:
   - Check `localStorage` contains new `bt_auth_token`
   - No 401 errors in console
   - Dashboard continues functioning

**Expected Results:**
- Tokens automatically refresh on 401 responses
- No user-visible errors during refresh
- Session continues seamlessly

### Scenario 3: Recommendation Feedback Flow

**Steps:**

1. **Precondition**: User logged in and KYC verified
2. **View recommendations**:
   - Navigate to Trading Dashboard
   - Recommendations list loads with items
3. **Complete pre-trade checklist**:
   - Toggle required checkboxes
   - Add optional notes
4. **Accept recommendation**:
   - Click "Aceptar" button
5. **Verify submission**:
   - Loading state during submission
   - Success feedback
   - Recommendation marked as accepted
6. **Check network tab**:
   - POST `/api/recommendations/feedback` returns 200
   - `Authorization: Bearer <token>` header present

**Expected Results:**
- Feedback persists to database
- UI updates after submission
- No authentication errors

### Scenario 4: Risk Metrics Display

**Steps:**

1. Navigate to Trading Dashboard (authenticated + KYC verified)
2. **View risk overview**:
   - Total capital displayed
   - Current drawdown percentage shown
   - Exposure metrics visible
3. **Verify real-time updates**:
   - Wait 30 seconds for auto-refresh
   - Metrics update without page reload
   - WebSocket events received
4. **Verify limit checks**:
   - If drawdown > 18%, warning banner appears
   - Risk limit indicators displayed

**Expected Results:**
- Risk metrics accurate and current
- Real-time updates working
- Alerts trigger correctly

### Scenario 5: Cross-Tab Token Sync (Optional)

**Steps:**

1. Open application in two browser tabs
2. Login in tab 1
3. **Verify tab 2 auto-detects auth**:
   - Dashboard appears automatically
   - No manual login required
4. Logout in tab 1
5. **Verify tab 2 detects logout**:
   - AuthGate appears
   - Protected resources blocked

**Expected Results:**
- Auth state syncs across tabs via localStorage events
- Consistent experience across tabs

## Manual Testing Checklist

### Authentication

- [ ] Login form displays when no token
- [ ] Register creates account and issues tokens
- [ ] KYC verification form appears for unverified users
- [ ] Tokens persist across page reloads
- [ ] Refresh token used automatically on 401

### Authorization

- [ ] Protected endpoints return 403 without KYC
- [ ] KYC verification grants access
- [ ] Role-based permissions enforced
- [ ] Unauthorized access redirects to AuthGate

### Data Display

- [ ] Recommendations load with correct fields:
  - [ ] suggested_position_size_usd
  - [ ] suggested_position_size_pct
  - [ ] risk_metrics
  - [ ] risk_limits
  - [ ] risk_limit_checks
  - [ ] pre_trade_checklist
- [ ] Risk overview shows current metrics
- [ ] Live metrics update every 30 seconds
- [ ] WebSocket events display in real-time

### Error Handling

- [ ] 401 errors trigger automatic refresh
- [ ] 403 errors show KYC gate
- [ ] Network errors show user-friendly messages
- [ ] Invalid tokens prompt re-login

### UI/UX

- [ ] Loading states shown during API calls
- [ ] Error messages clear and actionable
- [ ] Checklist items toggle correctly
- [ ] Form validation works
- [ ] Mobile responsive (viewport testing)

## Performance Expectations

- Initial page load: < 2 seconds
- API response times: < 500ms
- Token refresh: < 200ms
- WebSocket connection: < 1 second

## Known Limitations

- localStorage persists indefinitely (consider sessionStorage for sensitive apps)
- No CSRF protection in current implementation
- Password reset flow not implemented
- Session timeout not enforced client-side

## Test Data

**Test Users:**
- `viewer` - Role: viewer (read-only)
- `trader` - Role: trader (can create orders)
- `testuser1` - Custom test user


