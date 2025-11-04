"""Tests for KYC persistence across token refresh and session renewal."""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from backend.app import app
from backend.repositories.kyc_repository import KYCRepository
from backend.repositories.user_repository import UserRepository
from backend.repositories.user_tokens_repository import UserTokensRepository
from backend.auth.permissions import init_auth_service
from backend.compliance.kyc_aml import get_kyc_service


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh auth service."""
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    init_auth_service()
    return TestClient(app)


def test_kyc_persists_after_token_refresh(client):
    """Test that KYC verification persists after token refresh."""
    # Register user
    r = client.post('/api/auth/register', json={
        'username': 'kyc_persist_test',
        'email': 'kyc_persist@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    data = r.json()
    user_id = data['user_id']
    refresh_token = data['refresh_token']
    
    # Verify KYC
    r = client.post('/api/auth/verify', json={'user_id': user_id})
    assert r.status_code == 200
    
    # Verify KYC status before refresh
    kyc_repo = KYCRepository()
    assert kyc_repo.is_verified(user_id) == True
    
    # Refresh token
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    new_data = r.json()
    new_access_token = new_data['access_token']
    new_user_id = new_data['user_id']
    
    # User_id must remain the same
    assert new_user_id == user_id
    
    # KYC should still be verified after refresh
    assert kyc_repo.is_verified(user_id) == True
    
    # Access protected endpoint with new token
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {new_access_token}'})
    # Should succeed (200) or fail with service error (500), but not KYC error (403 with "KYC verification required")
    assert r.status_code in (200, 500), f"Expected 200 or 500, got {r.status_code}: {r.text}"
    if r.status_code == 403:
        assert "KYC verification required" not in r.json().get('detail', ''), "KYC should be verified"


def test_kyc_persists_through_multiple_refreshes(client):
    """Test that KYC verification persists through multiple token refreshes."""
    # Register and verify KYC
    r = client.post('/api/auth/register', json={
        'username': 'multirefresh_kyc',
        'email': 'multirefresh_kyc@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    user_id = r.json()['user_id']
    refresh_token = r.json()['refresh_token']
    
    # Verify KYC
    r = client.post('/api/auth/verify', json={'user_id': user_id})
    assert r.status_code == 200
    
    kyc_repo = KYCRepository()
    
    # First refresh
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    refresh_token_1 = r.json()['refresh_token']
    assert kyc_repo.is_verified(user_id) == True
    
    # Second refresh
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token_1})
    assert r.status_code == 200
    refresh_token_2 = r.json()['refresh_token']
    assert kyc_repo.is_verified(user_id) == True
    
    # Third refresh
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token_2})
    assert r.status_code == 200
    access_token_3 = r.json()['access_token']
    assert kyc_repo.is_verified(user_id) == True
    
    # Access protected endpoint
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {access_token_3}'})
    assert r.status_code in (200, 500), f"KYC should persist: got {r.status_code}"


def test_kyc_service_operates_on_persisted_users(client):
    """Test that KYCService operates on persisted users from database."""
    # Register user (creates persistent user)
    r = client.post('/api/auth/register', json={
        'username': 'persisted_user_test',
        'email': 'persisted_user@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    user_id = r.json()['user_id']
    
    # Verify user exists in persistent store
    user_repo = UserRepository()
    db_user = user_repo.find_by_user_id(user_id)
    assert db_user is not None
    assert db_user.user_id == user_id
    
    # Use KYCService to verify (should operate on persisted user)
    kyc_service = get_kyc_service()
    
    # Register for KYC
    kyc_service.register_user(user_id, 'persisted_user_test', 'persisted_user@example.com', 'AR')
    
    # Verify KYC
    result = kyc_service.verify_user(user_id)
    assert result == True
    
    # Check verification status
    assert kyc_service.is_verified(user_id) == True
    
    # Verify it's persisted in database
    kyc_repo = KYCRepository()
    assert kyc_repo.is_verified(user_id) == True


def test_kyc_service_fails_on_non_persisted_user():
    """Test that KYCService fails when operating on non-persisted user."""
    kyc_service = get_kyc_service()
    
    # Try to register KYC for non-existent user
    with pytest.raises(ValueError, match="not found"):
        kyc_service.register_user('non_existent_user', 'test', 'test@example.com', 'AR')
    
    # Try to verify non-existent user
    result = kyc_service.verify_user('non_existent_user')
    assert result == False
    
    # Check verification status should be False
    assert kyc_service.is_verified('non_existent_user') == False


def test_kyc_verification_from_database_not_token(client):
    """Test that KYC verification is checked from database, not from token data."""
    # Register user
    r = client.post('/api/auth/register', json={
        'username': 'db_kyc_test',
        'email': 'db_kyc@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    user_id = r.json()['user_id']
    access_token = r.json()['access_token']
    
    # Initially KYC should not be verified
    kyc_repo = KYCRepository()
    assert kyc_repo.is_verified(user_id) == False
    
    # Access protected endpoint should fail
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {access_token}'})
    assert r.status_code == 403
    assert "KYC verification required" in r.json()['detail']
    
    # Verify KYC in database
    r = client.post('/api/auth/verify', json={'user_id': user_id})
    assert r.status_code == 200
    
    # KYC should now be verified in database
    assert kyc_repo.is_verified(user_id) == True
    
    # Access with same token should now work (verification from DB, not token)
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {access_token}'})
    # Should succeed (200) or fail with service error (500), but not KYC error
    assert r.status_code in (200, 500), f"KYC should be verified from DB: got {r.status_code}"


def test_complete_flow_kyc_refresh_access(client):
    """Test complete flow: verify KYC → refresh token → access protected routes."""
    # Register user
    r = client.post('/api/auth/register', json={
        'username': 'complete_flow',
        'email': 'complete_flow@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    user_id = r.json()['user_id']
    refresh_token = r.json()['refresh_token']
    
    # Step 1: Verify KYC
    r = client.post('/api/auth/verify', json={'user_id': user_id})
    assert r.status_code == 200
    
    kyc_repo = KYCRepository()
    assert kyc_repo.is_verified(user_id) == True
    
    # Step 2: Refresh token
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    new_access_token = r.json()['access_token']
    assert r.json()['user_id'] == user_id  # Same user_id
    
    # Step 3: Access protected routes
    # Recommendations
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {new_access_token}'})
    assert r.status_code in (200, 500), f"Expected 200 or 500, got {r.status_code}: {r.text}"
    
    # Risk status
    r = client.get('/api/risk/status', headers={'Authorization': f'Bearer {new_access_token}'})
    assert r.status_code in (200, 500, 503), f"Expected 200, 500, or 503, got {r.status_code}: {r.text}"
    
    # All should work without repeating KYC verification
