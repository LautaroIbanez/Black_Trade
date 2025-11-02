"""Tests for execution system."""
import pytest
from datetime import datetime

from recommendation.orchestrator import SignalOrchestrator, Order, OrderSide, OrderType
from backend.execution.engine import ExecutionEngine, OrderStatus
from backend.execution.coordinator import ExecutionCoordinator
from backend.integrations.simulated_adapter import SimulatedAdapter
from backend.services.recommendation_service import RecommendationResult


@pytest.fixture
def simulated_adapter():
    """Create simulated adapter."""
    return SimulatedAdapter(initial_capital=10000.0)


@pytest.fixture
def execution_engine(simulated_adapter):
    """Create execution engine."""
    return ExecutionEngine(
        exchange_adapter=simulated_adapter,
        max_retries=3,
        retry_delay=5,
    )


@pytest.fixture
def coordinator(execution_engine):
    """Create execution coordinator."""
    return ExecutionCoordinator(
        execution_engine=execution_engine,
        max_capital_per_strategy={},
        prevent_opposite_signals=True,
    )


@pytest.fixture
def sample_order():
    """Create sample order."""
    return Order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=50000.0,
        stop_loss=49000.0,
        take_profit=51000.0,
        strategy_name="EMA_RSI",
    )


class TestExecutionEngine:
    """Tests for ExecutionEngine."""
    
    def test_submit_order(self, execution_engine, sample_order):
        """Test order submission."""
        order_id = execution_engine.submit_order(sample_order)
        
        assert order_id is not None
        assert order_id == sample_order.order_id
        
        order_state = execution_engine.get_order(order_id)
        assert order_state is not None
        assert order_state.status == OrderStatus.PENDING
        assert order_state.order.symbol == "BTCUSDT"
    
    def test_get_orders_by_status(self, execution_engine, sample_order):
        """Test getting orders by status."""
        order_id = execution_engine.submit_order(sample_order)
        
        pending = execution_engine.get_pending_orders()
        assert len(pending) == 1
        assert pending[0].order.order_id == order_id
    
    def test_cancel_order(self, execution_engine, sample_order):
        """Test order cancellation."""
        order_id = execution_engine.submit_order(sample_order)
        
        success = execution_engine.cancel_order(order_id, reason="Test cancellation")
        assert success is True
        
        order_state = execution_engine.get_order(order_id)
        assert order_state.status == OrderStatus.CANCELLED
    
    def test_update_order_from_fill(self, execution_engine, sample_order):
        """Test updating order from fill."""
        order_id = execution_engine.submit_order(sample_order)
        order_state = execution_engine.get_order(order_id)
        
        # Simulate fill
        fill_data = {
            'quantity': 0.05,
            'price': 50000.0,
            'fee': 0.0,
        }
        
        success = execution_engine.update_order_from_fill(order_id, fill_data)
        assert success is True
        
        order_state = execution_engine.get_order(order_id)
        assert order_state.filled_quantity == 0.05
        assert order_state.status == OrderStatus.PARTIALLY_FILLED
        
        # Complete fill
        fill_data2 = {
            'quantity': 0.05,
            'price': 50010.0,
            'fee': 0.0,
        }
        execution_engine.update_order_from_fill(order_id, fill_data2)
        
        order_state = execution_engine.get_order(order_id)
        assert order_state.status == OrderStatus.FILLED
        assert abs(order_state.average_fill_price - 50005.0) < 0.01


class TestExecutionCoordinator:
    """Tests for ExecutionCoordinator."""
    
    def test_execute_order(self, coordinator, sample_order):
        """Test order execution via coordinator."""
        success, order_id, error = coordinator.execute_order(sample_order)
        
        assert success is True
        assert order_id is not None
        assert error is None
        
        order_state = coordinator.execution_engine.get_order(order_id)
        assert order_state.status == OrderStatus.PENDING
    
    def test_prevent_opposite_signals(self, coordinator, sample_order):
        """Test prevention of opposite signals."""
        # Submit BUY order
        success, order_id1, _ = coordinator.execute_order(sample_order)
        assert success is True
        
        # Try to submit SELL order for same symbol
        sell_order = Order(
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0,
            strategy_name="EMA_RSI",
        )
        
        success, order_id2, error = coordinator.execute_order(sell_order)
        assert success is False
        assert "Conflicting" in error or "conflicts" in error.lower()
    
    def test_max_simultaneous_orders(self, coordinator):
        """Test maximum simultaneous orders limit."""
        coordinator.max_simultaneous_orders = 2
        
        # Submit 2 orders
        for i in range(2):
            order = Order(
                symbol=f"BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0.1,
                price=50000.0 + i,
                strategy_name="EMA_RSI",
            )
            success, _, _ = coordinator.execute_order(order)
            assert success is True
        
        # Third order should be blocked
        order3 = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50002.0,
            strategy_name="EMA_RSI",
        )
        success, _, error = coordinator.execute_order(order3)
        assert success is False
        assert "Maximum simultaneous orders" in error
    
    def test_get_strategy_exposure(self, coordinator, sample_order):
        """Test getting strategy exposure."""
        coordinator.execute_order(sample_order)
        
        exposure = coordinator.get_strategy_exposure("EMA_RSI")
        assert exposure['orders_count'] == 1
        assert exposure['total_value'] > 0


class TestSignalOrchestrator:
    """Tests for SignalOrchestrator."""
    
    def test_recommendation_to_order(self):
        """Test converting recommendation to order."""
        orchestrator = SignalOrchestrator()
        
        # Create sample recommendation
        recommendation = RecommendationResult(
            action="BUY",
            confidence=0.85,
            entry_range={'min': 49500.0, 'max': 50500.0},
            stop_loss=49000.0,
            take_profit=51000.0,
            current_price=50000.0,
            primary_strategy="EMA_RSI",
            supporting_strategies=["Momentum"],
            strategy_details=[],
            signal_consensus=0.85,
            risk_level="MEDIUM",
            risk_reward_ratio=2.0,
        )
        
        order = orchestrator.recommendation_to_order(recommendation, symbol="BTCUSDT")
        
        assert order is not None
        assert order.side == OrderSide.BUY
        assert order.symbol == "BTCUSDT"
        assert order.strategy_name == "EMA_RSI"
        assert order.stop_loss == 49000.0
        assert order.take_profit == 51000.0
    
    def test_hold_recommendation(self):
        """Test that HOLD recommendations are skipped."""
        orchestrator = SignalOrchestrator()
        
        recommendation = RecommendationResult(
            action="HOLD",
            confidence=0.5,
            entry_range={},
            stop_loss=0.0,
            take_profit=0.0,
            current_price=50000.0,
            primary_strategy="EMA_RSI",
            supporting_strategies=[],
            strategy_details=[],
            signal_consensus=0.5,
            risk_level="LOW",
        )
        
        order = orchestrator.recommendation_to_order(recommendation)
        assert order is None

