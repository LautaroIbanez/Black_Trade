"""Execution engine for order management and state tracking."""
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from recommendation.orchestrator import Order, OrderSide
from backend.logging.journal import transaction_journal, JournalEntryType

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderState:
    """Represents order state with history."""
    order: Order
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    exchange_order_id: Optional[str] = None
    fills: List[Dict[str, Any]] = field(default_factory=list)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'order': self.order.to_dict(),
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_fill_price': self.average_fill_price,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'rejection_reason': self.rejection_reason,
            'retry_count': self.retry_count,
            'exchange_order_id': self.exchange_order_id,
            'fills': self.fills,
        }
    
    def update_status(self, new_status: OrderStatus, reason: Optional[str] = None):
        """Update order status and record in history."""
        old_status = self.status
        self.status = new_status
        
        # Record state change
        self.state_history.append({
            'timestamp': datetime.now().isoformat(),
            'old_status': old_status.value,
            'new_status': new_status.value,
            'reason': reason,
        })
        
        # Update timestamps
        if new_status == OrderStatus.SUBMITTED:
            self.submitted_at = datetime.now()
        elif new_status == OrderStatus.FILLED:
            self.filled_at = datetime.now()
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = datetime.now()
        
        if reason:
            self.rejection_reason = reason


class ExecutionEngine:
    """Engine for managing order execution lifecycle."""
    
    def __init__(
        self,
        exchange_adapter,
        max_retries: int = 3,
        retry_delay: int = 5,  # seconds
        order_timeout: int = 300,  # seconds
    ):
        """
        Initialize execution engine.
        
        Args:
            exchange_adapter: Exchange adapter for order submission
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
            order_timeout: Timeout for orders (seconds)
        """
        self.exchange_adapter = exchange_adapter
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.order_timeout = order_timeout
        
        # Order storage (in production, use persistent queue)
        self.orders: Dict[str, OrderState] = {}
        
        self.logger = logging.getLogger(__name__)
    
    def submit_order(self, order: Order) -> str:
        """
        Submit order to execution queue.
        
        Args:
            order: Order to submit
            
        Returns:
            Order ID
        """
        # Generate order ID
        order_id = str(uuid.uuid4())
        order.order_id = order_id
        
        # Create order state
        order_state = OrderState(
            order=order,
            status=OrderStatus.PENDING,
            max_retries=self.max_retries,
        )
        
        # Store order
        self.orders[order_id] = order_state
        
        # Log to journal
        transaction_journal.log_order_created(order)
        
        self.logger.info(f"Order submitted to queue: {order_id} - {order.side.value} {order.quantity:.6f} {order.symbol}")
        
        return order_id
    
    def get_order(self, order_id: str) -> Optional[OrderState]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def get_orders_by_status(self, status: OrderStatus) -> List[OrderState]:
        """Get all orders with given status."""
        return [state for state in self.orders.values() if state.status == status]
    
    def get_pending_orders(self) -> List[OrderState]:
        """Get all pending orders."""
        return self.get_orders_by_status(OrderStatus.PENDING)
    
    def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        order_state = self.orders.get(order_id)
        if not order_state:
            self.logger.warning(f"Order not found: {order_id}")
            return False
        
        # Can only cancel pending or submitted orders
        if order_state.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            self.logger.warning(f"Cannot cancel order in status: {order_state.status}")
            return False
        
        # Update status
        order_state.update_status(OrderStatus.CANCELLED, reason or "Manual cancellation")
        
        # Cancel on exchange if submitted
        if order_state.status == OrderStatus.SUBMITTED and order_state.exchange_order_id:
            try:
                # In production, call exchange adapter cancel method
                # self.exchange_adapter.cancel_order(order_state.exchange_order_id)
                pass
            except Exception as e:
                self.logger.error(f"Error cancelling order on exchange: {e}")
        
        self.logger.info(f"Order cancelled: {order_id}")
        return True
    
    async def process_pending_orders(self):
        """Process pending orders (to be called periodically)."""
        pending = self.get_pending_orders()
        
        for order_state in pending:
            try:
                # Check if ready for retry
                if order_state.next_retry_at and datetime.now() < order_state.next_retry_at:
                    continue
                
                # Attempt submission
                success = await self._execute_order(order_state)
                
                if not success:
                    # Schedule retry
                    if order_state.retry_count < order_state.max_retries:
                        order_state.retry_count += 1
                        order_state.next_retry_at = datetime.now() + timedelta(seconds=self.retry_delay * order_state.retry_count)
                        self.logger.warning(f"Order {order_state.order.order_id} will retry in {self.retry_delay * order_state.retry_count}s")
                    else:
                        order_state.update_status(OrderStatus.REJECTED, "Max retries exceeded")
                        self.logger.error(f"Order {order_state.order.order_id} rejected after {order_state.max_retries} retries")
            except Exception as e:
                self.logger.error(f"Error processing order {order_state.order.order_id}: {e}")
                order_state.update_status(OrderStatus.REJECTED, str(e))
    
    async def _execute_order(self, order_state: OrderState) -> bool:
        """
        Execute order on exchange.
        
        Args:
            order_state: Order state to execute
            
        Returns:
            True if submitted successfully
        """
        order = order_state.order
        
        try:
            # Update status
            order_state.update_status(OrderStatus.SUBMITTED)
            
            # Submit to exchange
            # In production, this would call exchange adapter
            # exchange_response = await self.exchange_adapter.submit_order(order)
            # order_state.exchange_order_id = exchange_response['order_id']
            
            # For now, simulate successful submission
            order_state.exchange_order_id = f"EXCHANGE_{order.order_id}"
            
            # Log to journal
            transaction_journal.log_order_submitted(order.order_id, order_state.exchange_order_id)
            
            self.logger.info(f"Order submitted to exchange: {order.order_id} -> {order_state.exchange_order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error submitting order {order.order_id}: {e}")
            order_state.update_status(OrderStatus.REJECTED, str(e))
            return False
    
    def update_order_from_fill(self, order_id: str, fill_data: Dict[str, Any]) -> bool:
        """
        Update order state from fill notification.
        
        Args:
            order_id: Order ID
            fill_data: Fill data from exchange
            
        Returns:
            True if updated successfully
        """
        order_state = self.orders.get(order_id)
        if not order_state:
            self.logger.warning(f"Order not found for fill: {order_id}")
            return False
        
        # Record fill
        fill_quantity = float(fill_data.get('quantity', 0))
        fill_price = float(fill_data.get('price', 0))
        
        order_state.fills.append({
            'quantity': fill_quantity,
            'price': fill_price,
            'timestamp': datetime.now().isoformat(),
            'fee': fill_data.get('fee', 0),
        })
        
        # Update filled quantity and average price
        total_filled = order_state.filled_quantity + fill_quantity
        if total_filled > 0:
            total_cost = (order_state.average_fill_price * order_state.filled_quantity) + (fill_price * fill_quantity)
            order_state.average_fill_price = total_cost / total_filled
        
        order_state.filled_quantity = total_filled
        
        # Update status
        if total_filled >= order_state.order.quantity * 0.999:  # Allow small rounding
            order_state.update_status(OrderStatus.FILLED)
            # Log to journal
            transaction_journal.log_order_filled(order_id, {
                'quantity': total_filled,
                'average_price': order_state.average_fill_price,
                'fills': order_state.fills,
            })
            self.logger.info(f"Order filled: {order_id} - {total_filled:.6f} @ {order_state.average_fill_price:.2f}")
        else:
            order_state.update_status(OrderStatus.PARTIALLY_FILLED)
            # Log partial fill
            transaction_journal.log(
                JournalEntryType.ORDER_UPDATED,
                order_id=order_id,
                details={'status': 'partially_filled', 'filled_quantity': total_filled},
            )
            self.logger.info(f"Order partially filled: {order_id} - {total_filled:.6f}/{order_state.order.quantity:.6f}")
        
        return True
    
    def check_timeouts(self):
        """Check for timed out orders and cancel them."""
        now = datetime.now()
        
        for order_state in self.orders.values():
            if order_state.status == OrderStatus.SUBMITTED:
                if order_state.submitted_at:
                    elapsed = (now - order_state.submitted_at).total_seconds()
                    if elapsed > self.order_timeout:
                        self.logger.warning(f"Order timed out: {order_state.order.order_id}")
                        self.cancel_order(order_state.order.order_id, reason="Order timeout")

