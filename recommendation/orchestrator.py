"""Signal orchestrator that converts recommendations to executable orders."""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from backend.services.recommendation_service import RecommendationResult
from backend.risk.engine import RiskEngine

logger = logging.getLogger(__name__)


class OrderType(str, Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(str, Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


class Order:
    """Represents an executable order."""
    
    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy_name: str = "",
        recommendation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize order.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT/STOP_LOSS/TAKE_PROFIT)
            quantity: Order quantity
            price: Limit price (for LIMIT orders)
            stop_price: Stop price (for STOP orders)
            stop_loss: Stop loss level
            take_profit: Take profit level
            strategy_name: Strategy that generated this order
            recommendation_id: ID of source recommendation
            metadata: Additional metadata
        """
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.strategy_name = strategy_name
        self.recommendation_id = recommendation_id
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.order_id: Optional[str] = None  # Set after submission
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side.value,
            'order_type': self.order_type.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'strategy_name': self.strategy_name,
            'recommendation_id': self.recommendation_id,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create from dictionary."""
        order = cls(
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            order_type=OrderType(data['order_type']),
            quantity=data['quantity'],
            price=data.get('price'),
            stop_price=data.get('stop_price'),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit'),
            strategy_name=data.get('strategy_name', ''),
            recommendation_id=data.get('recommendation_id'),
            metadata=data.get('metadata', {}),
        )
        order.order_id = data.get('order_id')
        if 'created_at' in data:
            order.created_at = datetime.fromisoformat(data['created_at'])
        return order


class SignalOrchestrator:
    """Orchestrates conversion of recommendations to executable orders."""
    
    def __init__(
        self,
        risk_engine: Optional[RiskEngine] = None,
        max_capital_per_strategy: Optional[Dict[str, float]] = None,
        default_order_type: OrderType = OrderType.LIMIT,
    ):
        """
        Initialize signal orchestrator.
        
        Args:
            risk_engine: Risk engine for position sizing and validation
            max_capital_per_strategy: Maximum capital allocation per strategy (pct of total)
            default_order_type: Default order type for new orders
        """
        self.risk_engine = risk_engine
        self.max_capital_per_strategy = max_capital_per_strategy or {}
        self.default_order_type = default_order_type
        self.logger = logging.getLogger(__name__)
    
    def recommendation_to_order(
        self,
        recommendation: RecommendationResult,
        symbol: str = "BTCUSDT",
        risk_amount: Optional[float] = None,
        use_entry_range: bool = True,
    ) -> Optional[Order]:
        """
        Convert recommendation to executable order.
        
        Args:
            recommendation: RecommendationResult from recommendation service
            symbol: Trading pair
            risk_amount: Maximum amount to risk (if None, uses recommendation position_size)
            use_entry_range: If True, use entry_range for limit price
            
        Returns:
            Order object or None if recommendation is HOLD or invalid
        """
        # Skip HOLD recommendations
        if recommendation.action == "HOLD" or recommendation.confidence <= 0:
            self.logger.debug(f"Skipping HOLD recommendation (confidence: {recommendation.confidence})")
            return None
        
        # Determine order side
        if recommendation.action == "BUY":
            side = OrderSide.BUY
        elif recommendation.action == "SELL":
            side = OrderSide.SELL
        else:
            self.logger.warning(f"Unknown action: {recommendation.action}")
            return None
        
        # Calculate position size
        if risk_amount is None:
            # Use position size from recommendation if available
            if hasattr(recommendation, 'position_size_usd') and recommendation.position_size_usd > 0:
                position_value = recommendation.position_size_usd
            else:
                # Fallback: use risk engine if available
                if self.risk_engine:
                    sizing = self.risk_engine.calculate_position_size(
                        entry_price=recommendation.current_price,
                        stop_loss=recommendation.stop_loss,
                        risk_amount=recommendation.current_price * 0.01,  # 1% default risk
                        strategy_name=recommendation.primary_strategy,
                    )
                    position_value = sizing['position_value']
                else:
                    # Very conservative fallback
                    self.logger.warning("No risk engine available, using conservative sizing")
                    position_value = recommendation.current_price * 0.01  # $100 worth
        else:
            # Use provided risk amount
            if self.risk_engine:
                sizing = self.risk_engine.calculate_position_size(
                    entry_price=recommendation.current_price,
                    stop_loss=recommendation.stop_loss,
                    risk_amount=risk_amount,
                    strategy_name=recommendation.primary_strategy,
                )
                position_value = sizing['position_value']
            else:
                # Simple calculation
                risk_per_unit = abs(recommendation.current_price - recommendation.stop_loss)
                if risk_per_unit > 0:
                    position_value = (risk_amount / risk_per_unit) * recommendation.current_price
                else:
                    position_value = recommendation.current_price * 0.01
        
        # Calculate quantity
        quantity = position_value / recommendation.current_price if recommendation.current_price > 0 else 0
        
        # Determine order price
        order_price = None
        if use_entry_range and recommendation.entry_range:
            # Use midpoint of entry range for limit orders
            entry_min = recommendation.entry_range.get('min', recommendation.current_price)
            entry_max = recommendation.entry_range.get('max', recommendation.current_price)
            order_price = (entry_min + entry_max) / 2
        else:
            # Use current price
            order_price = recommendation.current_price
        
        # Create order
        order = Order(
            symbol=symbol,
            side=side,
            order_type=self.default_order_type,
            quantity=quantity,
            price=order_price if self.default_order_type == OrderType.LIMIT else None,
            stop_loss=recommendation.stop_loss,
            take_profit=recommendation.take_profit,
            strategy_name=recommendation.primary_strategy,
            recommendation_id=getattr(recommendation, 'recommendation_id', None),
            metadata={
                'confidence': recommendation.confidence,
                'signal_consensus': recommendation.signal_consensus,
                'risk_reward_ratio': recommendation.risk_reward_ratio,
                'supporting_strategies': recommendation.supporting_strategies,
                'position_value': position_value,
                'current_price': recommendation.current_price,
            },
        )
        
        self.logger.info(
            f"Created order: {side.value} {quantity:.6f} {symbol} @ {order_price:.2f} "
            f"(strategy: {recommendation.primary_strategy}, confidence: {recommendation.confidence:.2f})"
        )
        
        return order
    
    def validate_order(self, order: Order) -> tuple[bool, Optional[str]]:
        """
        Validate order against risk limits and coordination rules.
        
        Args:
            order: Order to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if risk engine is available
        if not self.risk_engine:
            return True, None  # Skip validation if no risk engine
        
        # Get current risk metrics
        metrics = self.risk_engine.get_risk_metrics()
        
        # Check capital availability
        position_value = order.quantity * (order.price or order.metadata.get('current_price', 0))
        if position_value > metrics.equity * 0.5:  # More than 50% of equity
            return False, f"Order value ({position_value:.2f}) exceeds 50% of equity ({metrics.equity:.2f})"
        
        # Check strategy capital limits
        if order.strategy_name in self.max_capital_per_strategy:
            max_capital_pct = self.max_capital_per_strategy[order.strategy_name]
            max_capital = metrics.total_capital * (max_capital_pct / 100.0)
            
            # Calculate current exposure for this strategy
            exposure_data = self.risk_engine.calculate_exposure()
            current_exposure = exposure_data['exposure_by_strategy'].get(order.strategy_name, 0)
            
            if current_exposure + position_value > max_capital:
                return False, f"Order would exceed strategy capital limit ({max_capital_pct}%)"
        
        # Check overall exposure limits
        checks = self.risk_engine.check_risk_limits(metrics)
        if checks['exposure']['violated']:
            return False, f"Overall exposure limit violated: {metrics.exposure_pct:.2f}%"
        
        # Validate stop loss and take profit
        if order.stop_loss and order.take_profit:
            if order.side == OrderSide.BUY:
                if order.stop_loss >= order.metadata.get('current_price', 0):
                    return False, "Stop loss must be below entry price for BUY orders"
                if order.take_profit <= order.metadata.get('current_price', 0):
                    return False, "Take profit must be above entry price for BUY orders"
            else:  # SELL
                if order.stop_loss <= order.metadata.get('current_price', 0):
                    return False, "Stop loss must be above entry price for SELL orders"
                if order.take_profit >= order.metadata.get('current_price', 0):
                    return False, "Take profit must be below entry price for SELL orders"
        
        return True, None
    
    def check_duplicate_signals(
        self,
        new_order: Order,
        pending_orders: List[Order],
        open_positions: List[Dict],
    ) -> tuple[bool, Optional[str]]:
        """
        Check for duplicate or conflicting signals.
        
        Args:
            new_order: New order to check
            pending_orders: List of pending orders
            open_positions: List of open positions
            
        Returns:
            Tuple of (has_conflict, conflict_description)
        """
        # Check for opposite pending orders
        for pending in pending_orders:
            if pending.symbol == new_order.symbol:
                if (pending.side == OrderSide.BUY and new_order.side == OrderSide.SELL) or \
                   (pending.side == OrderSide.SELL and new_order.side == OrderSide.BUY):
                    return True, f"Conflicting pending order: {pending.side.value} vs {new_order.side.value}"
        
        # Check for opposite open positions
        for position in open_positions:
            if position.get('symbol') == new_order.symbol:
                pos_side = position.get('side', '').lower()
                if (pos_side == 'long' and new_order.side == OrderSide.SELL) or \
                   (pos_side == 'short' and new_order.side == OrderSide.BUY):
                    return True, f"Open {pos_side} position conflicts with {new_order.side.value} order"
        
        # Check for duplicate same-side orders
        for pending in pending_orders:
            if pending.symbol == new_order.symbol and pending.side == new_order.side:
                # Allow if significantly different price (>2% difference)
                if pending.price and new_order.price:
                    price_diff_pct = abs(pending.price - new_order.price) / pending.price
                    if price_diff_pct < 0.02:
                        return True, f"Duplicate {new_order.side.value} order for {new_order.symbol}"
        
        return False, None

