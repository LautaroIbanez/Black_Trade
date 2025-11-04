"""Tests for authentication and permission dependencies."""
import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

from backend.app import app
from backend.auth.permissions import init_auth_service, get_auth_service, Role, Permission
from backend.repositories.kyc_repository import KYCRepository


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    # Reset auth service before each test
    from backend.auth.permissions import _auth_service
    global _auth_service
    _auth_service = None
    
    init_auth_service()
    return TestClient(app)


@pytest.fixture
def viewer_token(client):
    """Get viewer user token."""
    auth_service = get_auth_service()
    token, _ = auth_service.create_user("test_viewer", Role.VIEWER)
    return token


@pytest.fixture
def trader_token(client):
    """Get trader user token."""
    auth_service = get_auth_service()
    token, user = auth_service.create_user("test_trader", Role.TRADER)
    # Verify KYC for trader
    KYCRepository().upsert(user.user_id, "test_trader", "trader@test.com", "US", verified=True)
    return token


@pytest.fixture
def admin_token(client):
    """Get admin user token."""
    auth_service = get_auth_service()
    token, user = auth_service.create_user("test_admin", Role.ADMIN)
    # Verify KYC for admin
    KYCRepository().upsert(user.user_id, "test_admin", "admin@test.com", "US", verified=True)
    return token


@pytest.fixture
def unverified_token(client):
    """Get unverified user token."""
    auth_service = get_auth_service()
    token, user = auth_service.create_user("test_unverified", Role.TRADER)
    # Explicitly leave unverified
    KYCRepository().upsert(user.user_id, "test_unverified", "unverified@test.com", "US", verified=False)
    return token


def test_get_live_recommendations_without_auth(client):
    """Test that recommendations endpoint requires authentication."""
    response = client.get("/api/recommendations/live")
    assert response.status_code == 403  # FastAPI returns 403 for missing credentials


def test_get_live_recommendations_without_permission(client, viewer_token):
    """Test that viewer without KYC cannot access recommendations."""
    response = client.get(
        "/api/recommendations/live",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    # Should fail due to KYC verification (viewer doesn't have KYC by default)
    assert response.status_code == 403


def test_get_live_recommendations_with_permission_and_kyc(client, trader_token):
    """Test that trader with KYC can access recommendations."""
    response = client.get(
        "/api/recommendations/live",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data


def test_get_live_recommendations_unverified_kyc(client, unverified_token):
    """Test that unverified user cannot access recommendations."""
    response = client.get(
        "/api/recommendations/live",
        headers={"Authorization": f"Bearer {unverified_token}"}
    )
    assert response.status_code == 403
    assert "KYC verification required" in response.json()["detail"]


def test_get_risk_status_without_auth(client):
    """Test that risk endpoint requires authentication."""
    response = client.get("/api/risk/status")
    assert response.status_code == 403


def test_get_risk_status_without_permission(client, viewer_token):
    """Test that viewer cannot access risk metrics."""
    response = client.get(
        "/api/risk/status",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]


def test_get_risk_status_with_permission_and_kyc(client, trader_token):
    """Test that trader with KYC can access risk metrics."""
    response = client.get(
        "/api/risk/status",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "limits" in data


def test_get_risk_exposure_with_permission(client, trader_token):
    """Test risk exposure endpoint."""
    response = client.get(
        "/api/risk/exposure",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200


def test_get_risk_drawdown_with_permission(client, trader_token):
    """Test risk drawdown endpoint."""
    response = client.get(
        "/api/risk/drawdown",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200


def test_get_risk_limits_with_permission(client, trader_token):
    """Test risk limits endpoint."""
    response = client.get(
        "/api/risk/limits",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "global_limits" in data


def test_update_risk_limits_without_permission(client, trader_token):
    """Test that trader cannot update risk limits."""
    response = client.post(
        "/api/risk/limits",
        headers={"Authorization": f"Bearer {trader_token}"},
        json={"max_exposure_pct": 50.0}
    )
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]


def test_update_risk_limits_with_permission(client, admin_token):
    """Test that admin can update risk limits."""
    response = client.post(
        "/api/risk/limits",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"max_exposure_pct": 50.0}
    )
    # Should succeed or fail with validation, but not permission error
    assert response.status_code in [200, 400]  # 400 if risk engine not initialized


def test_create_order_without_permission(client, viewer_token):
    """Test that viewer cannot create orders."""
    response = client.post(
        "/api/execution/orders",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.1,
            "price": 50000.0,
            "strategy_name": "test"
        }
    )
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]


def test_recommendation_tracking_with_permission(client, trader_token):
    """Test recommendation tracking endpoints."""
    # Accept
    response = client.post(
        "/api/recommendation-tracking/accept",
        headers={"Authorization": f"Bearer {trader_token}"},
        json={
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "payload": {"test": "data"}
        }
    )
    assert response.status_code == 200
    
    # Reject
    response = client.post(
        "/api/recommendation-tracking/reject",
        headers={"Authorization": f"Bearer {trader_token}"},
        json={
            "symbol": "ETHUSDT",
            "timeframe": "1h",
            "payload": {"test": "data"}
        }
    )
    assert response.status_code == 200
    
    # History
    response = client.get(
        "/api/recommendation-tracking/history",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200
    assert "items" in response.json()
    
    # Metrics
    response = client.get(
        "/api/recommendation-tracking/metrics",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    assert response.status_code == 200


def test_user_object_has_attributes(client, trader_token):
    """Test that user object returned by dependency has required attributes."""
    # This test ensures the dependency returns User object, not a function
    response = client.get(
        "/api/recommendations/live",
        headers={"Authorization": f"Bearer {trader_token}"}
    )
    # If we got here without AttributeError, the user object was properly returned
    assert response.status_code == 200
