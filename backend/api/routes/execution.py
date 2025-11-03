"""API routes for order execution and journal."""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from recommendation.orchestrator import Order, OrderSide, OrderType
from backend.execution.engine import ExecutionEngine, OrderStatus
from backend.execution.coordinator import ExecutionCoordinator
from backend.logging.journal import transaction_journal, JournalEntryType
from backend.auth.permissions import AuthService, Permission
from backend.config.security import rate_limit
from backend.compliance.kyc_aml import get_kyc_service, get_aml_service
from backend.repositories.journal_repository import JournalRepository

router = APIRouter(tags=["execution"])


class OrderRequest(BaseModel):
    """Request model for creating an order."""
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str = "limit"
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str = ""


class CancelOrderRequest(BaseModel):
    """Request model for cancelling an order."""
    order_id: str
    reason: Optional[str] = None


# Global execution coordinator (would be injected via dependency in production)
_execution_coordinator: Optional[ExecutionCoordinator] = None


def get_execution_coordinator() -> ExecutionCoordinator:
    """Get execution coordinator instance."""
    global _execution_coordinator
    if _execution_coordinator is None:
        raise HTTPException(status_code=503, detail="Execution coordinator not initialized")
    return _execution_coordinator


def set_execution_coordinator(coordinator: ExecutionCoordinator):
    """Set execution coordinator instance."""
    global _execution_coordinator
    _execution_coordinator = coordinator


@router.post("/orders")
@rate_limit(max_requests=30, window_seconds=60)
async def create_order(
    req: Request,
    request: OrderRequest,
    coordinator: ExecutionCoordinator = Depends(get_execution_coordinator),
    user=Depends(lambda: AuthService().require_permission(Permission.CREATE_ORDERS)),
) -> Dict[str, Any]:
    """Create and submit an order."""
    try:
        # Create order object
        order = Order(
            symbol=request.symbol,
            side=OrderSide(request.side.lower()),
            order_type=OrderType(request.order_type.lower()),
            quantity=request.quantity,
            price=request.price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            strategy_name=request.strategy_name,
        )
        
        # KYC verification
        kyc = get_kyc_service()
        if not kyc.is_verified(user.user_id):
            raise HTTPException(status_code=403, detail="User not KYC-verified")
        
        # AML check (best-effort estimate)
        try:
            aml = get_aml_service()
            est_notional = (request.price or 0.0) * float(request.quantity)
            suspicious, alert = aml.check_transaction(user.user_id, order.order_id or "PENDING", est_notional, "ORDER_SUBMIT", {})
            if suspicious:
                # Soft-block or allow based on policy; here we allow but log
                transaction_journal.log(JournalEntryType.SYSTEM_EVENT, order_id=order.order_id, details={"aml_alert": alert.alert_id if alert else None})
        except Exception:
            pass
        
        # Execute via coordinator
        success, order_id, error = coordinator.execute_order(order)
        
        if not success:
            raise HTTPException(status_code=400, detail=error or "Failed to execute order")
        
        # Log to journal
        transaction_journal.log_order_created(order)
        
        return {
            "success": True,
            "order_id": order_id,
            "order": order.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    coordinator: ExecutionCoordinator = Depends(get_execution_coordinator),
) -> Dict[str, Any]:
    """Get order by ID."""
    order_state = coordinator.execution_engine.get_order(order_id)
    
    if not order_state:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order_id,
        "state": order_state.to_dict(),
    }


@router.get("/orders")
async def list_orders(
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    coordinator: ExecutionCoordinator = Depends(get_execution_coordinator),
) -> Dict[str, Any]:
    """List orders with optional filters."""
    all_orders = list(coordinator.execution_engine.orders.values())
    
    # Apply filters
    if status:
        try:
            status_enum = OrderStatus(status.lower())
            all_orders = [o for o in all_orders if o.status == status_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if strategy:
        all_orders = [o for o in all_orders if o.order.strategy_name == strategy]
    
    return {
        "orders": [{"order_id": state.order.order_id, **state.to_dict()} for state in all_orders],
        "count": len(all_orders),
    }


@router.post("/orders/{order_id}/cancel")
@rate_limit(max_requests=30, window_seconds=60)
async def cancel_order(
    req: Request,
    order_id: str,
    request: CancelOrderRequest,
    coordinator: ExecutionCoordinator = Depends(get_execution_coordinator),
    user=Depends(lambda: AuthService().require_permission(Permission.CANCEL_ORDERS)),
) -> Dict[str, Any]:
    """Cancel an order."""
    success = coordinator.execution_engine.cancel_order(order_id, request.reason)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel order")
    
    # Log to journal
    transaction_journal.log_order_cancelled(order_id, request.reason or "Manual cancellation", user="api")
    
    return {
        "success": True,
        "order_id": order_id,
        "cancelled_at": datetime.now().isoformat(),
    }


@router.get("/journal")
@rate_limit(max_requests=60, window_seconds=60)
async def get_journal(
    order_id: Optional[str] = None,
    entry_type: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Get journal entries."""
    try:
        repo = JournalRepository()
        entry_type_str = None
        if entry_type:
            # Validate type
            entry_type_str = JournalEntryType(entry_type.lower()).value
        entries = repo.get_entries(order_id=order_id, entry_type=entry_type_str, limit=limit)
        return {"entries": entries, "count": len(entries)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/journal/{order_id}")
@rate_limit(max_requests=60, window_seconds=60)
async def get_order_history(order_id: str) -> Dict[str, Any]:
    """Get complete history for an order."""
    history = transaction_journal.get_order_history(order_id)
    
    return {
        "order_id": order_id,
        "history": history,
        "count": len(history),
    }


@router.get("/stats")
async def get_execution_stats(
    coordinator: ExecutionCoordinator = Depends(get_execution_coordinator),
) -> Dict[str, Any]:
    """Get execution statistics."""
    stats = coordinator.get_global_stats()
    
    return stats


@router.get("/coordination/strategy/{strategy_name}")
async def get_strategy_exposure(
    strategy_name: str,
    coordinator: ExecutionCoordinator = Depends(get_execution_coordinator),
) -> Dict[str, Any]:
    """Get exposure for a specific strategy."""
    exposure = coordinator.get_strategy_exposure(strategy_name)
    
    return {
        "strategy_name": strategy_name,
        "exposure": exposure,
    }

