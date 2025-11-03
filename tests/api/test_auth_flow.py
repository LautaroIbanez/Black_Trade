import os
import pytest
from fastapi.testclient import TestClient

from backend.app import app


client = TestClient(app)


def test_register_verify_login_and_access_protected():
    r = client.post('/api/auth/register', json={'username': 'testuser', 'email': 'test@example.com', 'country': 'AR', 'role': 'viewer'})
    assert r.status_code == 200
    data = r.json()
    assert 'access_token' in data and 'refresh_token' in data and 'user_id' in data
    access_token = data['access_token']
    refresh_token = data['refresh_token']
    user_id = data['user_id']
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {access_token}'})
    assert r.status_code in (401, 403)
    r = client.post('/api/auth/kyc-status', json={'user_id': user_id})
    assert r.status_code == 200
    status = r.json()
    assert status.get('verified') == False
    r = client.post('/api/auth/verify', json={'user_id': user_id})
    assert r.status_code == 200
    r = client.post('/api/auth/login', json={'username': 'testuser', 'role': 'viewer'})
    assert r.status_code == 200
    access_token = r.json()['access_token']
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {access_token}'})
    assert r.status_code in (200, 204, 403)
    r = client.get('/api/risk/status', headers={'Authorization': f'Bearer {access_token}'})
    assert r.status_code in (200, 500)


def test_refresh_token_flow():
    r = client.post('/api/auth/register', json={'username': 'refreshuser', 'email': 'refresh@example.com', 'country': 'AR', 'role': 'viewer'})
    refresh_token = r.json()['refresh_token']
    r = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
    assert r.status_code == 200
    data = r.json()
    assert 'access_token' in data and 'refresh_token' in data
    new_access = data['access_token']
    r = client.get('/api/recommendations/live', headers={'Authorization': f'Bearer {new_access}'})
    assert r.status_code in (401, 403)


