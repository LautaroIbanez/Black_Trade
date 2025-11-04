"""Tests for AuthService singleton pattern."""
import pytest
from backend.auth.permissions import (
    AuthService,
    get_auth_service,
    init_auth_service,
    Role,
    Permission,
)


def test_get_auth_service_returns_singleton():
    """Test that get_auth_service returns the same instance."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    instance1 = get_auth_service()
    instance2 = get_auth_service()
    
    assert instance1 is instance2
    assert id(instance1) == id(instance2)


def test_init_auth_service_sets_singleton():
    """Test that init_auth_service sets the singleton."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    instance1 = init_auth_service()
    instance2 = get_auth_service()
    
    assert instance1 is instance2
    assert id(instance1) == id(instance2)


def test_reinit_auth_service_replaces_singleton():
    """Test that reinitializing replaces the singleton."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    instance1 = init_auth_service()
    old_id = id(instance1)
    
    # Reinitialize
    instance2 = init_auth_service()
    new_id = id(instance2)
    
    # Should be different instances
    assert instance1 is not instance2
    assert old_id != new_id
    
    # But get_auth_service should return the new one
    instance3 = get_auth_service()
    assert instance3 is instance2
    assert instance3 is not instance1


def test_token_issuance_after_reinit():
    """Test that tokens work correctly after reinitialization."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    # Initialize and create a user
    auth_service1 = init_auth_service()
    token1, user1 = auth_service1.create_user("test_user", Role.TRADER)
    
    # Reinitialize
    auth_service2 = init_auth_service()
    
    # Old token should not work (new instance, different token storage)
    authenticated_user = auth_service2.authenticate(token1)
    assert authenticated_user is None
    
    # Create new user after reinit
    token2, user2 = auth_service2.create_user("test_user2", Role.TRADER)
    authenticated_user2 = auth_service2.authenticate(token2)
    assert authenticated_user2 is not None
    assert authenticated_user2.user_id == user2.user_id


def test_get_auth_service_preserves_tokens():
    """Test that tokens are preserved when using get_auth_service multiple times."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    auth_service = init_auth_service()
    token, user = auth_service.create_user("test_user", Role.TRADER)
    
    # Get service again
    auth_service2 = get_auth_service()
    
    # Token should still work
    authenticated_user = auth_service2.authenticate(token)
    assert authenticated_user is not None
    assert authenticated_user.user_id == user.user_id


def test_permission_check_after_reinit():
    """Test that permission checking works after reinitialization."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    # Initialize and create users
    auth_service = init_auth_service()
    token_trader, user_trader = auth_service.create_user("trader", Role.TRADER)
    token_viewer, user_viewer = auth_service.create_user("viewer", Role.VIEWER)
    
    # Check permissions
    assert user_trader.has_permission(Permission.CREATE_ORDERS)
    assert not user_viewer.has_permission(Permission.CREATE_ORDERS)
    
    # Reinitialize
    auth_service2 = init_auth_service()
    
    # Create new users
    token_trader2, user_trader2 = auth_service2.create_user("trader2", Role.TRADER)
    token_viewer2, user_viewer2 = auth_service2.create_user("viewer2", Role.VIEWER)
    
    # New users should have correct permissions
    assert user_trader2.has_permission(Permission.CREATE_ORDERS)
    assert not user_viewer2.has_permission(Permission.CREATE_ORDERS)


def test_multiple_calls_to_get_auth_service():
    """Test that multiple calls to get_auth_service return same instance."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    instances = [get_auth_service() for _ in range(10)]
    
    # All should be the same instance
    first_id = id(instances[0])
    for instance in instances[1:]:
        assert id(instance) == first_id
        assert instance is instances[0]


def test_lazy_initialization():
    """Test that get_auth_service lazily initializes if not set."""
    # Reset the singleton
    from backend.auth.permissions import _auth_service
    import backend.auth.permissions as auth_module
    auth_module._auth_service = None
    
    # Should create new instance
    instance = get_auth_service()
    assert instance is not None
    assert isinstance(instance, AuthService)
    
    # Should be same instance on subsequent calls
    instance2 = get_auth_service()
    assert instance is instance2
