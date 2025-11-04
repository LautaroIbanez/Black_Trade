# Development Guidelines

## Obtaining Singleton Services in FastAPI

This document outlines best practices for accessing singleton services throughout the Black Trade codebase, particularly from FastAPI endpoints and routes.

### Service Initialization Pattern

Most services in Black Trade use a singleton pattern to ensure consistency across the application. Services are initialized during application startup and accessed via getter functions.

### AuthService Pattern

The `AuthService` is the canonical example of this pattern:

#### Initialization

Services are initialized during application startup in `backend/app.py`:

```python
from backend.auth.permissions import init_auth_service

# During startup
init_auth_service()
```

The `init_auth_service()` function:
1. Creates a new `AuthService` instance
2. Creates default users (viewer, trader, risk_manager, admin)
3. Assigns the instance to the module-level `_auth_service` variable

#### Access Pattern

**✅ CORRECT: Use the getter function**

```python
from backend.auth.permissions import get_auth_service

# In any module (routes, services, etc.)
auth_service = get_auth_service()
user = auth_service.authenticate(token)
```

**❌ INCORRECT: Direct instantiation**

```python
# DON'T DO THIS - Creates a new instance, breaking singleton
from backend.auth.permissions import AuthService

auth_service = AuthService()  # ❌ Wrong!
```

### Using Services in FastAPI Dependencies

When using services in FastAPI endpoint dependencies, pass the getter function directly:

```python
from fastapi import Depends
from backend.auth.permissions import get_auth_service, AuthService

async def my_endpoint(
    auth_service: AuthService = Depends(get_auth_service)
):
    # FastAPI will call get_auth_service() and inject the singleton
    user = auth_service.authenticate(token)
    return {"user": user.username}
```

### Other Singleton Services

The same pattern applies to other singleton services:

#### KYCService

```python
from backend.compliance.kyc_aml import get_kyc_service

kyc_service = get_kyc_service()
is_verified = kyc_service.is_verified(user_id)
```

#### AMLService

```python
from backend.compliance.kyc_aml import get_aml_service

aml_service = get_aml_service()
suspicious, alert = aml_service.check_transaction(...)
```

#### MarketDataService

```python
from backend.services.market_data_service import MarketDataService

# This is initialized at app level, but you can access the instance
market_data = MarketDataService()  # This is okay if it's designed as a module singleton
```

### Service Lifecycle

1. **Startup**: Services are initialized in `initialize_services()` called during FastAPI startup
2. **Runtime**: Services are accessed via getter functions throughout the application
3. **Testing**: Tests can reset singletons by setting `_service = None` before tests

### Testing Singleton Services

When writing tests, you may need to reset singleton instances:

```python
import pytest
from backend.auth.permissions import _auth_service
import backend.auth.permissions as auth_module

@pytest.fixture
def reset_auth_service():
    """Reset auth service before test."""
    auth_module._auth_service = None
    yield
    auth_module._auth_service = None
```

### Creating New Singleton Services

If you need to create a new singleton service, follow this pattern:

```python
# my_service.py
_service_instance: Optional[MyService] = None

def get_my_service() -> MyService:
    """Get global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MyService()
    return _service_instance

def init_my_service() -> MyService:
    """Initialize service with configuration."""
    global _service_instance
    _service_instance = MyService(config=...)
    return _service_instance
```

Then use it in endpoints:

```python
from fastapi import Depends
from my_service import get_my_service, MyService

@router.get("/my-endpoint")
async def my_endpoint(
    service: MyService = Depends(get_my_service)
):
    return service.do_something()
```

### Key Principles

1. **Never instantiate services directly** - Always use getter functions
2. **Initialize during startup** - Use `init_*` functions in `app.py`
3. **Access via getters** - Use `get_*` functions throughout the codebase
4. **Use Depends() for FastAPI** - Pass getter functions to `Depends()` for dependency injection
5. **Document singleton services** - Clearly mark services that use this pattern

### Common Mistakes to Avoid

1. ❌ `AuthService()` - Creates new instance
2. ❌ `Depends(lambda: AuthService())` - Creates new instance per request
3. ❌ Caching service instances in module variables without getters
4. ❌ Importing service instances directly instead of getter functions

### Summary

- Use `get_*()` functions to access singleton services
- Initialize services during app startup with `init_*()` functions
- Pass getter functions to FastAPI `Depends()` for dependency injection
- Never instantiate services directly with `ServiceClass()` in production code
- Reset singletons in tests by setting `_service_instance = None`
