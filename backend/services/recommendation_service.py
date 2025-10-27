"""Real-time recommendation service with multiple strategy signals."""
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from strategies.strategy_base import StrategyBase
from backend.services.strategy_registry import strategy_registry
from backend.services.risk_management import risk_management_service, RiskTarget


@dataclass
class StrategySignal:
    """Signal from a single strategy."""
    strategy_name: str
    signal: int  # -1, 0, 1
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    reason: str
    price: float
    timestamp: Any
    score: float  # Historical performance score
    timeframe: str
    entry_range: Dict[str, float]  # Strategy-specific entry range
    risk_targets: Dict[str, float]  # Strategy-specific risk targets


@dataclass
class RecommendationResult:
    """Final recommendation result."""
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    entry_range: Dict[str, float]
    stop_loss: float
    take_profit: float
    current_price: float
    primary_strategy: str
    supporting_strategies: List[str]
    strategy_details: List[Dict[str, Any]]
    signal_consensus: float
    risk_level: str


class RecommendationService:
    """Service for generating real-time trading recommendations."""
    
    def __init__(self):
        """Initialize recommendation service."""
        self.strategy_registry = strategy_registry
        self.risk_levels = {
            "LOW": {"max_confidence": 0.6, "min_supporting": 1},
            "MEDIUM": {"max_confidence": 0.8, "min_supporting": 2},
            "HIGH": {"max_confidence": 1.0, "min_supporting": 3}
        }
    
    def generate_recommendation(self, data: Dict[str, pd.DataFrame], 
                              historical_metrics: Optional[Dict[str, List[Dict]]] = None) -> RecommendationResult:
        """Generate trading recommendation from current signals and historical data."""
        
        # Get enabled strategies
        strategies = self.strategy_registry.get_enabled_strategies()
        
        # Generate signals for each timeframe
        all_signals = []
        for timeframe, df in data.items():
            if df.empty:
                continue
                
            for strategy in strategies:
                try:
                    signal_data = strategy.generate_signal(df)
                    
                    # Calculate strategy-specific entry range
                    entry_range = strategy.entry_range(df, signal_data['signal'])
                    
                    # Calculate strategy-specific risk targets
                    risk_targets = strategy.risk_targets(df, signal_data['signal'], signal_data['price'])
                    
                    signal = StrategySignal(
                        strategy_name=strategy.name,
                        signal=signal_data['signal'],
                        strength=signal_data['strength'],
                        confidence=signal_data['confidence'],
                        reason=signal_data['reason'],
                        price=signal_data['price'],
                        timestamp=signal_data['timestamp'],
                        score=self._get_strategy_score(strategy.name, historical_metrics),
                        timeframe=timeframe,
                        entry_range=entry_range,
                        risk_targets=risk_targets
                    )
                    all_signals.append(signal)
                except Exception as e:
                    print(f"Error generating signal for {strategy.name} on {timeframe}: {e}")
                    continue
        
        if not all_signals:
            return self._create_default_recommendation()
        
        # Analyze signals and generate recommendation
        return self._analyze_signals(all_signals, data)
    
    def _get_strategy_score(self, strategy_name: str, historical_metrics: Optional[Dict[str, List[Dict]]]) -> float:
        """Get historical performance score for a strategy."""
        if not historical_metrics:
            return 0.5  # Default neutral score
        
        # Find the strategy in historical metrics
        for timeframe, results in historical_metrics.items():
            for result in results:
                if result.get('strategy_name') == strategy_name:
                    return result.get('score', 0.5)
        
        return 0.5  # Default if not found
    
    def _create_risk_targets_from_signals(self, signals: List[StrategySignal]) -> List[RiskTarget]:
        """Create RiskTarget objects from StrategySignal objects."""
        risk_targets = []
        
        for signal in signals:
            risk_target = RiskTarget(
                strategy_name=signal.strategy_name,
                stop_loss=signal.risk_targets['stop_loss'],
                take_profit=signal.risk_targets['take_profit'],
                confidence=signal.confidence,
                strength=signal.strength,
                timeframe=signal.timeframe
            )
            risk_targets.append(risk_target)
        
        return risk_targets
    
    def _create_default_recommendation(self) -> RecommendationResult:
        """Create default recommendation when no signals are available."""
        return RecommendationResult(
            action="HOLD",
            confidence=0.0,
            entry_range={"min": 0.0, "max": 0.0},
            stop_loss=0.0,
            take_profit=0.0,
            current_price=0.0,
            primary_strategy="None",
            supporting_strategies=[],
            strategy_details=[],
            signal_consensus=0.0,
            risk_level="LOW"
        )
    
    def _calculate_aggregated_entry_range(self, signals: List[StrategySignal]) -> Dict[str, float]:
        """Calculate aggregated entry range from multiple strategy signals."""
        if not signals:
            return {"min": 0.0, "max": 0.0}
        
        # Weight ranges by strategy confidence and score
        weighted_min = 0.0
        weighted_max = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = signal.confidence * signal.score
            weighted_min += signal.entry_range['min'] * weight
            weighted_max += signal.entry_range['max'] * weight
            total_weight += weight
        
        if total_weight > 0:
            return {
                "min": weighted_min / total_weight,
                "max": weighted_max / total_weight
            }
        else:
            # Fallback to simple average
            return {
                "min": sum(s.entry_range['min'] for s in signals) / len(signals),
                "max": sum(s.entry_range['max'] for s in signals) / len(signals)
            }
    
    def _analyze_signals(self, signals: List[StrategySignal], data: Dict[str, pd.DataFrame]) -> RecommendationResult:
        """Analyze signals and generate final recommendation."""
        
        # Group signals by type
        buy_signals = [s for s in signals if s.signal == 1]
        sell_signals = [s for s in signals if s.signal == -1]
        hold_signals = [s for s in signals if s.signal == 0]
        
        # Calculate consensus
        total_signals = len(signals)
        buy_ratio = len(buy_signals) / total_signals if total_signals > 0 else 0
        sell_ratio = len(sell_signals) / total_signals if total_signals > 0 else 0
        hold_ratio = len(hold_signals) / total_signals if total_signals > 0 else 0
        
        # Determine primary action
        if buy_ratio > sell_ratio and buy_ratio > hold_ratio:
            action = "BUY"
            primary_signals = buy_signals
        elif sell_ratio > buy_ratio and sell_ratio > hold_ratio:
            action = "SELL"
            primary_signals = sell_signals
        else:
            action = "HOLD"
            primary_signals = hold_signals
        
        # Calculate weighted confidence
        if primary_signals:
            # Weight by strategy score and signal confidence
            weighted_confidence = sum(s.confidence * s.score for s in primary_signals) / len(primary_signals)
            primary_strategy = max(primary_signals, key=lambda s: s.confidence * s.score).strategy_name
        else:
            weighted_confidence = 0.0
            primary_strategy = "None"
        
        # Calculate signal consensus
        signal_consensus = max(buy_ratio, sell_ratio, hold_ratio)
        
        # Determine supporting strategies
        supporting_strategies = [s.strategy_name for s in primary_signals if s.strategy_name != primary_strategy]
        
        # Calculate entry range, stop loss, and take profit using strategy-specific ranges
        if primary_signals:
            current_price = primary_signals[0].price
            entry_range = self._calculate_aggregated_entry_range(primary_signals)
            
            # Use risk management service for adaptive stop loss and take profit
            risk_targets = self._create_risk_targets_from_signals(primary_signals)
            aggregated_risk = risk_management_service.aggregate_risk_targets(
                risk_targets, data, current_price
            )
            stop_loss = aggregated_risk.stop_loss
            take_profit = aggregated_risk.take_profit
        else:
            current_price = 0.0
            entry_range = {"min": 0.0, "max": 0.0}
            stop_loss = 0.0
            take_profit = 0.0
        
        # Determine risk level
        risk_level = self._determine_risk_level(weighted_confidence, len(primary_signals))
        
        # Prepare strategy details
        strategy_details = []
        for signal in signals:
            strategy_details.append({
                "strategy_name": signal.strategy_name,
                "signal": signal.signal,
                "strength": signal.strength,
                "confidence": signal.confidence,
                "reason": signal.reason,
                "score": signal.score,
                "timeframe": signal.timeframe,
                "weight": signal.confidence * signal.score,
                "entry_range": signal.entry_range,
                "risk_targets": signal.risk_targets
            })
        
        # Sort strategy details by weight
        strategy_details.sort(key=lambda x: x['weight'], reverse=True)
        
        return RecommendationResult(
            action=action,
            confidence=min(weighted_confidence, 1.0),
            entry_range=entry_range,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_price=current_price,
            primary_strategy=primary_strategy,
            supporting_strategies=supporting_strategies,
            strategy_details=strategy_details,
            signal_consensus=signal_consensus,
            risk_level=risk_level
        )
    
    def _calculate_trade_levels(self, current_price: float, action: str, confidence: float) -> Tuple[Dict[str, float], float, float]:
        """Calculate entry range, stop loss, and take profit levels."""
        
        # Base percentages
        base_entry_range = 0.002  # 0.2%
        base_stop_loss = 0.02     # 2%
        base_take_profit = 0.04   # 4%
        
        # Adjust based on confidence
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5 to 1.0
        
        entry_range_pct = base_entry_range * confidence_multiplier
        stop_loss_pct = base_stop_loss * confidence_multiplier
        take_profit_pct = base_take_profit * confidence_multiplier
        
        if action == "BUY":
            entry_range = {
                "min": current_price * (1 - entry_range_pct),
                "max": current_price * (1 + entry_range_pct)
            }
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        elif action == "SELL":
            entry_range = {
                "min": current_price * (1 - entry_range_pct),
                "max": current_price * (1 + entry_range_pct)
            }
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)
        else:  # HOLD
            entry_range = {
                "min": current_price * (1 - entry_range_pct),
                "max": current_price * (1 + entry_range_pct)
            }
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        
        return entry_range, stop_loss, take_profit
    
    def _determine_risk_level(self, confidence: float, supporting_count: int) -> str:
        """Determine risk level based on confidence and supporting strategies."""
        
        if confidence >= 0.8 and supporting_count >= 3:
            return "HIGH"
        elif confidence >= 0.6 and supporting_count >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _create_default_recommendation(self) -> RecommendationResult:
        """Create default recommendation when no signals are available."""
        return RecommendationResult(
            action="HOLD",
            confidence=0.0,
            entry_range={"min": 0.0, "max": 0.0},
            stop_loss=0.0,
            take_profit=0.0,
            current_price=0.0,
            primary_strategy="None",
            supporting_strategies=[],
            strategy_details=[],
            signal_consensus=0.0,
            risk_level="LOW"
        )
    
    def get_strategy_consensus(self, signals: List[StrategySignal]) -> Dict[str, Any]:
        """Get detailed consensus analysis of all strategies."""
        
        if not signals:
            return {"consensus": 0, "agreement": 0.0, "disagreement": 0.0}
        
        # Count signal types
        buy_count = len([s for s in signals if s.signal == 1])
        sell_count = len([s for s in signals if s.signal == -1])
        hold_count = len([s for s in signals if s.signal == 0])
        
        total = len(signals)
        
        # Calculate consensus
        max_count = max(buy_count, sell_count, hold_count)
        consensus_signal = 1 if buy_count == max_count else (-1 if sell_count == max_count else 0)
        agreement_ratio = max_count / total
        
        return {
            "consensus": consensus_signal,
            "agreement": agreement_ratio,
            "buy_ratio": buy_count / total,
            "sell_ratio": sell_count / total,
            "hold_ratio": hold_count / total,
            "total_strategies": total
        }


# Global service instance
recommendation_service = RecommendationService()
