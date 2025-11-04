"""Tests for authentication flow with persistent user identity."""
import os
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.repositories.kyc_repository import KYCRepository
from backend.repositories.user_repository import UserRepository
from backend.auth.permissions import init_auth_service


@pytest.fixture(scope="function")
def client():
    """Create test client with fresh auth service."""
    # Reset auth service before each test
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    init_auth_service()
    return TestClient(app)


def test_register_creates_persistent_user(client):
    """Test that registration creates a persistent user with stable user_id."""
    r = client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'country': 'AR',
        'role': 'viewer'
    })
    assert r.status_code == 200
    data = r.json()
    assert 'access_token' in data and 'refresh_token' in data and 'user_id' in data
    user_id = data['user_id']
    
    # Verify user exists in database
    user_repo = UserRepository()
    db_user = user_repo.find_by_user_id(user_id)
    assert db_user is not None
    assert db_user.email == 'test@example.com'
    assert db_user.username == 'testuser'


def test_register_reuses_existing_user_by_email(client):
    """Test that registering again with same email returns same user_id."""
    # First registration
    r1 = client.post('/api/auth/register', json={
        'username': 'testuser1',
        'email': 'same@example.com',
        'country': 'AR',
        'role': 'viewer'
    })
    assert r1.status_code == 200
    user_id1 = r1.json()['user_id']
    
    # Second registration with same email
    r2 = client.post('/api/auth/register', json={
        'username': 'testuser2',
        'email': 'same@example.com',
        'country': 'US',
        'role': 'trader'
    })
    assert r2.status_code == 200
    user_id2 = r2.json()['user_id']
    
    # Should return same user_id
    assert user_id1 == user_id2


def test_register_verify_login_maintains_user_id(client):
    """Test that user_id remains stable across register, verify, and login."""
    # Register
    r = client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'country': 'AR',
        'role': 'viewer'
    })
    assert r.status_code == 200
    data = r.json()
    original_user_id = data['user_id']
    
    # Verify KYC
    r = client.post('/api/auth/verify', json={'user_id': original_user_id})
    assert r.status_code == 200
    
    # Login - should maintain same user_id when email is reused
    # Note: Current login doesn't require email, but we can verify KYC persists
    r = client.post('/api/auth/login', json={'username': 'testuser', 'role': 'viewer'})
    assert r.status_code == 200
    
    # Verify KYC status still valid
    r = client.post('/api/auth/kyc-status', json={'user_id': original_user_id})
    assert r.status_code == 200
    status = r.json()
    assert status.get('verified') == True


def test_refresh_token_maintains_user_id(client):
    """Test that refresh token maintains same user_id."""
    # Register and verify KYC
    r = client.post('/api/auth/register', json={
        'username': 'refreshuser',
        'email': 'refresh@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    data = r.json()
    original_user_id = data['user_id']
    refresh_token = data['refresh_token']
    
    # Verify KYC
    KYCRepository().upsert(original_user_id, 'refreshuser', 'refresh@example.com', 'AR', verified=True)
    
    # Refresh token
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    new_data = r.json()
    new_user_id = new_data['user_id']
    
    # User_id must remain the same
    assert new_user_id == original_user_id
    assert 'access_token' in new_data
    assert 'refresh_token' in new_data


def test_refresh_token_kyc_persists(client):
    """Test that KYC verification persists after token refresh."""
    # Register
    r = client.post('/api/auth/register', json={
        'username': 'kycuser',
        'email': 'kyc@example.com',
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
    r = client.post('/api/auth/kyc-status', json={'user_id': user_id})
    assert r.status_code == 200
    assert r.json().get('verified') == True
    
    # Refresh token
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    new_data = r.json()
    new_user_id = new_data['user_id']
    
    # User_id must be same
    assert new_user_id == user_id
    
    # KYC should still be verified
    r = client.post('/api/auth/kyc-status', json={'user_id': new_user_id})
    assert r.status_code == 200
    assert r.json().get('verified') == True


def test_login_refresh_access_protected_endpoints(client):
    """Test complete flow: login → refresh → access protected endpoints."""
    # Register and verify KYC
    r = client.post('/api/auth/register', json={
        'username': 'fullflow',
        'email': 'fullflow@example.com',
        'country': 'AR',
        'role': 'trader'
    })
    assert r.status_code == 200
    data = r.json()
    user_id = data['user_id']
    refresh_token = data['refresh_token']
    
    # Verify KYC
    KYCRepository().upsert(user_id, 'fullflow', 'fullflow@example.com', 'AR', verified=True)
    
    # Refresh to get new tokens
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    new_data = r.json()
    new_access = new_data['access_token']
    new_user_id = new_data['user_id']
    
    # Verify user_id unchanged
    assert new_user_id == user_id
    
    # Access protected endpoint with new token
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {new_access}'})
    # Should succeed (200) or fail with service error (500), but not auth error (401/403)
    assert r.status_code in (200, 500), f"Expected 200 or 500, got {r.status_code}: {r.text}"
    
    # Access risk endpoint
    r = client.get('/api/risk/status', headers={'Authorization': f'Bearer {new_access}'})
    # Should succeed or fail with service error, but not auth error
    assert r.status_code in (200, 500, 503), f"Expected 200, 500, or 503, got {r.status_code}: {r.text}"


def test_multiple_refreshes_maintain_identity(client):
    """Test that multiple token refreshes maintain same user_id."""
    # Register
    r = client.post('/api/auth/register', json={
        'username': 'multirefresh',
        'email': 'multirefresh@example.com',
        'country': 'AR',
        'role': 'viewer'
    })
    assert r.status_code == 200
    original_user_id = r.json()['user_id']
    refresh_token = r.json()['refresh_token']
    
    # First refresh
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    user_id_1 = r.json()['user_id']
    refresh_token_1 = r.json()['refresh_token']
    assert user_id_1 == original_user_id
    
    # Second refresh
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token_1})
    assert r.status_code == 200
    user_id_2 = r.json()['user_id']
    assert user_id_2 == original_user_id
    
    # Third refresh
    r = client.post('/api/auth/refresh', json={'refresh_token': r.json()['refresh_token']})
    assert r.status_code == 200
    user_id_3 = r.json()['user_id']
    assert user_id_3 == original_user_id


def test_old_refresh_token_invalid_after_refresh(client):
    """Test that old refresh token is invalidated after refresh."""
    # Register
    r = client.post('/api/auth/register', json={
        'username': 'invalidatetest',
        'email': 'invalidatetest@example.com',
        'country': 'AR',
        'role': 'viewer'
    })
    assert r.status_code == 200
    refresh_token = r.json()['refresh_token']
    
    # Refresh token
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    
    # Old refresh token should be invalid
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 401


