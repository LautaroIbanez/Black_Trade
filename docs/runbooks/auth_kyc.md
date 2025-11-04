# Authentication & KYC Troubleshooting Runbook

This runbook provides procedures for diagnosing and resolving issues related to KYC verification persistence and authentication.

## Overview

KYC verification is persisted in the `kyc_users` table and tied to a persistent `user_id` in the `users` table. The verification status should persist across token refreshes, session renewals, and application restarts.

## Architecture

- **User Identity**: Stored in `users` table with immutable `user_id`
- **KYC Status**: Stored in `kyc_users` table, linked by `user_id`
- **Tokens**: Stored in `user_tokens` table, linked by `user_id`
- **Verification Source**: Always checked from database (`KYCRepository`), never from token payload

## Common Issues

### Issue 1: KYC Verification Not Persisting After Token Refresh

**Symptoms:**
- User verifies KYC successfully
- After token refresh, user cannot access protected endpoints
- Error: "KYC verification required"

**Diagnosis Steps:**

1. **Check user_id persistence:**
   ```sql
   SELECT user_id, username, email FROM users WHERE email = 'user@example.com';
   ```

2. **Check KYC status in database:**
   ```sql
   SELECT user_id, verified, verified_at FROM kyc_users WHERE user_id = '<user_id>';
   ```

3. **Verify token refresh maintains user_id:**
   ```bash
   # Check logs for token refresh
   grep "token_refresh" logs/app.log | grep "<user_id>"
   ```

4. **Check if user_id changed after refresh:**
   ```sql
   SELECT user_id, token_type, created_at 
   FROM user_tokens 
   WHERE token = '<refresh_token>' 
   ORDER BY created_at DESC;
   ```

**Resolution:**

If `user_id` is different between old and new tokens:
- This indicates a bug in `AppAuthService.refresh_tokens()`
- Verify that `refresh_tokens()` method retrieves `user_id` from token record, not creates new user

If `user_id` is same but KYC not verified:
- Check `kyc_users.verified` flag is `true`
- Verify `verified_at` timestamp exists
- Check application logs for KYC verification errors

**Manual Fix:**

```sql
-- Re-verify KYC if needed
UPDATE kyc_users 
SET verified = true, verified_at = NOW() 
WHERE user_id = '<user_id>';

-- Verify the fix
SELECT user_id, verified, verified_at FROM kyc_users WHERE user_id = '<user_id>';
```

### Issue 2: KYC Verification Lost After Application Restart

**Symptoms:**
- KYC was verified before restart
- After restart, users report KYC verification missing
- Protected endpoints return 403

**Diagnosis Steps:**

1. **Check database connection:**
   ```sql
   -- Verify database is accessible
   SELECT COUNT(*) FROM kyc_users;
   ```

2. **Check if KYC data exists:**
   ```sql
   SELECT user_id, verified, verified_at 
   FROM kyc_users 
   WHERE verified = true 
   ORDER BY verified_at DESC 
   LIMIT 10;
   ```

3. **Check application logs:**
   ```bash
   # Look for KYC-related errors
   grep -i "kyc\|verification" logs/app.log | tail -50
   ```

**Resolution:**

If data exists in database but not accessible:
- Verify `KYCRepository` is using correct database connection
- Check if `KYCService` is properly initialized
- Verify database migrations are applied

**Manual Fix:**

Ensure KYC records are properly linked:
```sql
-- Check orphaned KYC records
SELECT k.user_id, k.verified, u.user_id as user_exists
FROM kyc_users k
LEFT JOIN users u ON k.user_id = u.user_id
WHERE u.user_id IS NULL;

-- Clean up orphaned records if needed (CAUTION: Backup first)
-- DELETE FROM kyc_users WHERE user_id NOT IN (SELECT user_id FROM users);
```

### Issue 3: User Cannot Access Protected Endpoints Despite KYC Verification

**Symptoms:**
- User shows as verified in database
- Access tokens are valid
- Still getting "KYC verification required"

**Diagnosis Steps:**

1. **Verify user_id matches:**
   ```sql
   -- Get user_id from token
   SELECT user_id FROM user_tokens WHERE token = '<access_token>';

   -- Check KYC for that user_id
   SELECT verified, verified_at FROM kyc_users WHERE user_id = '<user_id_from_token>';
   ```

2. **Check dependency injection:**
   - Verify endpoint uses `require_recommendation_access_with_kyc` or checks KYC manually
   - Check if route handler is checking `KYCRepository().is_verified(user.user_id)`

3. **Test KYC repository directly:**
   ```python
   from backend.repositories.kyc_repository import KYCRepository
   repo = KYCRepository()
   is_verified = repo.is_verified('<user_id>')
   print(f"KYC verified: {is_verified}")
   ```

**Resolution:**

If database shows verified but code doesn't:
- Verify `KYCRepository.is_verified()` is being called correctly
- Check if there's a database connection issue
- Verify the `user_id` from token matches the `user_id` in `kyc_users` table

**Manual Fix:**

```sql
-- Force re-verification
UPDATE kyc_users 
SET verified = true, 
    verified_at = NOW(),
    updated_at = NOW()
WHERE user_id = '<user_id>';

-- Verify
SELECT * FROM kyc_users WHERE user_id = '<user_id>';
```

## Manual KYC Revocation Procedures

### Revoke KYC Verification for a User

**Use Case:** User's KYC verification needs to be revoked (e.g., compliance issue, suspicious activity)

**Steps:**

1. **Identify user:**
   ```sql
   SELECT user_id, username, email FROM users WHERE email = 'user@example.com';
   ```

2. **Revoke KYC:**
   ```sql
   UPDATE kyc_users 
   SET verified = false,
       verified_at = NULL,
       updated_at = NOW()
   WHERE user_id = '<user_id>';
   ```

3. **Optionally revoke all tokens (force re-authentication):**
   ```sql
   DELETE FROM user_tokens WHERE user_id = '<user_id>';
   ```

4. **Verify revocation:**
   ```sql
   SELECT user_id, verified, verified_at FROM kyc_users WHERE user_id = '<user_id>';
   ```

5. **Log the action:**
   ```python
   from backend.logging.journal import transaction_journal, JournalEntryType
   transaction_journal.log(
       JournalEntryType.SYSTEM_EVENT,
       details={
           "event": "kyc_revoked",
           "user_id": "<user_id>",
           "reason": "Manual revocation",
           "revoked_by": "admin"
       }
   )
   ```

### Revoke All Tokens for a User

**Use Case:** User account compromise, need to force logout

**Steps:**

1. **Revoke all tokens:**
   ```sql
   DELETE FROM user_tokens WHERE user_id = '<user_id>';
   ```

2. **Verify:**
   ```sql
   SELECT COUNT(*) FROM user_tokens WHERE user_id = '<user_id>';
   -- Should return 0
   ```

3. **Log the action:**
   ```python
   from backend.logging.journal import transaction_journal, JournalEntryType
   transaction_journal.log(
       JournalEntryType.SYSTEM_EVENT,
       details={
           "event": "tokens_revoked",
           "user_id": "<user_id>",
           "reason": "Security revocation",
           "revoked_by": "admin"
       }
   )
   ```

## Verification Procedures

### Verify KYC Persistence Across Refresh

**Test Procedure:**

1. Register a new user
2. Verify KYC status
3. Refresh token multiple times
4. Verify KYC status after each refresh

**Expected Result:** KYC status remains `verified = true` throughout

**SQL Verification:**
```sql
-- Before refresh
SELECT user_id, verified FROM kyc_users WHERE user_id = '<user_id>';

-- After refresh
SELECT user_id, verified FROM kyc_users WHERE user_id = '<user_id>';

-- Should be identical
```

### Verify User Identity Consistency

**Test Procedure:**

1. Register user with email
2. Note `user_id` from registration
3. Refresh token
4. Note `user_id` from refresh response
5. Access protected endpoint

**Expected Result:** `user_id` is identical in all steps

**SQL Verification:**
```sql
-- Check all tokens for same user_id
SELECT DISTINCT user_id, token_type, COUNT(*) as token_count
FROM user_tokens
WHERE user_id = '<user_id>'
GROUP BY user_id, token_type;

-- Should show same user_id for all tokens
```

## Monitoring

### Key Metrics to Monitor

1. **KYC Verification Rate:**
   ```sql
   SELECT 
       COUNT(*) FILTER (WHERE verified = true) as verified_count,
       COUNT(*) as total_count,
       ROUND(100.0 * COUNT(*) FILTER (WHERE verified = true) / COUNT(*), 2) as verification_rate
   FROM kyc_users;
   ```

2. **Users Without KYC:**
   ```sql
   SELECT u.user_id, u.username, u.email
   FROM users u
   LEFT JOIN kyc_users k ON u.user_id = k.user_id
   WHERE k.user_id IS NULL OR k.verified = false;
   ```

3. **Recent KYC Verifications:**
   ```sql
   SELECT user_id, verified_at, updated_at
   FROM kyc_users
   WHERE verified = true
   ORDER BY verified_at DESC
   LIMIT 10;
   ```

### Log Patterns to Watch

- `"KYC verification required"` - User accessing protected endpoint without KYC
- `"User not found in persistent store"` - User_id mismatch or missing user
- `"Token user_id mismatch"` - Refresh token validation error
- `"Persisted user {user_id} verified for KYC"` - Successful verification

## Escalation

If manual fixes don't resolve the issue:

1. **Check application configuration:**
   - Database connection strings
   - Service initialization order
   - Migration status

2. **Review code changes:**
   - Recent changes to `KYCService`
   - Changes to `UserRepository`
   - Changes to authentication flow

3. **Contact:**
   - Backend team for persistence issues
   - DevOps for database connectivity issues
   - Security team for KYC revocation procedures

## References

- Authentication Guide: `docs/authentication.md`
- Development Guidelines: `docs/development.md`
- KYC Service: `backend/compliance/kyc_aml.py`
- KYC Repository: `backend/repositories/kyc_repository.py`
- User Repository: `backend/repositories/user_repository.py`
