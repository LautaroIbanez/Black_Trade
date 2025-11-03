"""Coordination rules for managing multiple strategies and orders."""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from recommendation.orchestrator import Order, OrderSide
from backend.execution.engine import ExecutionEngine, OrderState, OrderStatus
from backend.logging.journal import transaction_journal, JournalEntryType

logger = logging.getLogger(__name__)


class ExecutionCoordinator:
    """Coordinates order execution across multiple strategies."""
    
    def __init__(
        self,
        execution_engine: ExecutionEngine,
        max_capital_per_strategy: Optional[Dict[str, float]] = None,
        prevent_opposite_signals: bool = True,
        max_simultaneous_orders: int = 5,
    ):
        """
        Initialize execution coordinator.
        
        Args:
            execution_engine: Execution engine instance
            max_capital_per_strategy: Max capital % per strategy
            prevent_opposite_signals: If True, prevent BUY/SELL conflicts
            max_simultaneous_orders: Maximum simultaneous pending orders
        """
        self.execution_engine = execution_engine
        self.max_capital_per_strategy = max_capital_per_strategy or {}
        self.prevent_opposite_signals = prevent_opposite_signals
        self.max_simultaneous_orders = max_simultaneous_orders
        self.logger = logging.getLogger(__name__)
    
    def can_execute_order(self, order: Order, open_positions: Optional[List[Dict]] = None) -> tuple[bool, Optional[str]]:
        """
        Check if order can be executed based on coordination rules.
        
        Args:
            order: Order to check
            open_positions: List of open positions from exchange
            
        Returns:
            Tuple of (can_execute, reason_if_not)
        """
        # Check maximum simultaneous orders
        pending_orders = self.execution_engine.get_pending_orders()
        if len(pending_orders) >= self.max_simultaneous_orders:
            return False, f"Maximum simultaneous orders reached ({self.max_simultaneous_orders})"
        
        # Check for opposite signals if enabled
        if self.prevent_opposite_signals:
            # Get pending orders
            conflicting_pending = [
                state for state in pending_orders
                if state.order.symbol == order.symbol and
                   ((state.order.side == OrderSide.BUY and order.side == OrderSide.SELL) or
                    (state.order.side == OrderSide.SELL and order.side == OrderSide.BUY))
            ]
            
            if conflicting_pending:
                return False, f"Conflicting {order.side.value} order already pending for {order.symbol}"
            
            # Check open positions
            if open_positions:
                for position in open_positions:
                    if position.get('symbol') == order.symbol:
                        pos_side = position.get('side', '').lower()
                        if (pos_side == 'long' and order.side == OrderSide.SELL) or \
                           (pos_side == 'short' and order.side == OrderSide.BUY):
                            return False, f"Open {pos_side} position conflicts with {order.side.value} order"
        
        # Check strategy capital allocation
        if order.strategy_name in self.max_capital_per_strategy:
            # Calculate current exposure for this strategy
            strategy_orders = [
                state for state in self.execution_engine.orders.values()
                if state.order.strategy_name == order.strategy_name and
                   state.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
            ]
            
            # This would need risk engine to calculate actual exposure
            # For now, just check number of pending orders
            strategy_pending = len([s for s in strategy_orders if s.status == OrderStatus.PENDING])
            if strategy_pending >= 2:  # Limit per strategy
                return False, f"Too many pending orders for strategy {order.strategy_name}"
        
        return True, None
    
    def execute_order(self, order: Order, open_positions: Optional[List[Dict]] = None) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Execute order with coordination checks.
        
        Args:
            order: Order to execute
            open_positions: List of open positions
            
        Returns:
            Tuple of (success, order_id, error_message)
        """
        # Check if can execute
        can_execute, reason = self.can_execute_order(order, open_positions)
        
        if not can_execute:
            self.logger.warning(f"Order blocked by coordinator: {reason}")
            # Log coordination block
            if order.order_id:
                transaction_journal.log_coordination_block(order.order_id, reason)
            return False, None, reason
        
        # Submit order
        try:
            order_id = self.execution_engine.submit_order(order)
            self.logger.info(f"Order executed: {order_id} - {order.side.value} {order.quantity:.6f} {order.symbol}")
            return True, order_id, None
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error executing order: {error_msg}")
            return False, None, error_msg
    
    def get_strategy_exposure(self, strategy_name: str) -> Dict[str, float]:
        """Get current exposure for a strategy."""
        strategy_orders = [
            state for state in self.execution_engine.orders.values()
            if state.order.strategy_name == strategy_name
        ]
        
        total_value = 0.0
        filled_value = 0.0
        
        for state in strategy_orders:
            order = state.order
            order_value = order.quantity * (order.price or 0)
            total_value += order_value
            
            if state.status == OrderStatus.FILLED:
                filled_value += state.filled_quantity * state.average_fill_price
        
        return {
            'total_value': total_value,
            'filled_value': filled_value,
            'pending_value': total_value - filled_value,
            'orders_count': len(strategy_orders),
        }
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global execution statistics."""
        all_orders = list(self.execution_engine.orders.values())
        
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len([o for o in all_orders if o.status == status])
        
        strategy_counts = {}
        for order_state in all_orders:
            strategy = order_state.order.strategy_name
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            'total_orders': len(all_orders),
            'status_counts': status_counts,
            'strategy_counts': strategy_counts,
            'pending_orders': len([o for o in all_orders if o.status == OrderStatus.PENDING]),
            'active_orders': len([o for o in all_orders if o.status in [OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]]),
        }

