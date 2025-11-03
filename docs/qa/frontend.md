# Frontend QA: Auth + Protected Data Flow

## Goal
Validate login, token persistence, and access to protected recommendations and risk data.

## Preconditions
- Backend running with `JWT_SECRET` set.
- Risk and ingestion schedulers initialized.

## Steps
1. Open the dashboard. AuthGate should appear.
2. Enter a username and click Login. Verify localStorage contains `bt_auth_token` and `bt_user_id`.
3. Attempt to open recommendations (the dashboard loads them automatically). If 403 appears, proceed to verify KYC.
4. (Optional) Register with email and country, then call `/api/auth/verify` via a simple cURL or admin tool with your `user_id`.
5. Reload dashboard; RecommendationsList should display items (or an empty state with 200), RiskOverview should load without 403.
6. Disconnect and reconnect network to verify WS AlertsCenter reconnects and continues receiving alerts.
7. Complete a checklist on a recommendation and submit feedback; verify a 200 response.

## Expected Results
- Tokens persist across reloads; no repeated 401/403 once KYC is verified.
- Risk and recommendation sections reflect live data with loading/error states.
- Alerts appear in real-time in AlertsCenter.


