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
class ContributionBreakdown:
    """Breakdown of how different strategies contributed to the recommendation."""
    strategy_name: str
    timeframe: str
    signal: int
    confidence: float
    strength: float
    score: float
    weight: float
    entry_contribution: Dict[str, float]
    sl_contribution: float
    tp_contribution: float
    reason: str

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
    trade_management: Optional[Dict[str, Any]] = None
    contribution_breakdown: Optional[List[ContributionBreakdown]] = None


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
                              historical_metrics: Optional[Dict[str, List[Dict]]] = None,
                              profile: str = "balanced") -> RecommendationResult:
        """Generate trading recommendation from current signals and historical data."""
        
        # Get enabled strategies
        strategies = self.strategy_registry.get_enabled_strategies()
        
        # Define timeframe weights based on trading profile
        timeframe_weights = self._get_profile_weights(profile)
        
        # Generate signals for each timeframe
        all_signals = []
        for timeframe, df in data.items():
            if df.empty:
                continue
            
            # Get timeframe weight
            timeframe_weight = timeframe_weights.get(timeframe, 0.5)
                
            for strategy in strategies:
                try:
                    signal_data = strategy.generate_signal(df)
                    
                    # Calculate strategy-specific entry range
                    entry_range = strategy.entry_range(df, signal_data['signal'])
                    
                    # Calculate strategy-specific risk targets
                    risk_targets = strategy.risk_targets(df, signal_data['signal'], signal_data['price'])
                    
                    # Apply timeframe weight to confidence and strength
                    weighted_confidence = signal_data['confidence'] * timeframe_weight
                    weighted_strength = signal_data['strength'] * timeframe_weight
                    
                    signal = StrategySignal(
                        strategy_name=strategy.name,
                        signal=signal_data['signal'],
                        strength=weighted_strength,
                        confidence=weighted_confidence,
                        reason=signal_data['reason'],
                        price=signal_data['price'],
                        timestamp=signal_data['timestamp'],
                        score=self._get_strategy_score(strategy.name, historical_metrics, timeframe),
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
    
    def _get_strategy_score(self, strategy_name: str, historical_metrics: Optional[Dict[str, List[Dict]]], timeframe: str = None) -> float:
        """Get historical performance score for a strategy in a specific timeframe."""
        if not historical_metrics:
            return 0.5  # Default neutral score
        
        # If timeframe is specified, look for that specific timeframe first
        if timeframe and timeframe in historical_metrics:
            for result in historical_metrics[timeframe]:
                if result.get('strategy_name') == strategy_name:
                    return result.get('score', 0.5)
        
        # Fallback: search all timeframes (original behavior)
        for tf, results in historical_metrics.items():
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
        """Calculate aggregated entry range from multiple strategy signals.
        Prioritize non-degenerate ranges; exclude empty/invalid ranges; apply robust fallbacks."""
        if not signals:
            return {"min": 0.0, "max": 0.0}

        # Filter out invalid or degenerate ranges
        def is_valid_range(rng: Dict[str, float]) -> bool:
            return isinstance(rng, dict) and 'min' in rng and 'max' in rng and isinstance(rng['min'], (int, float)) and isinstance(rng['max'], (int, float)) and rng['max'] > rng['min']

        valid_signals = [s for s in signals if is_valid_range(s.entry_range)]
        if not valid_signals:
            # Try to coerce degenerate ranges into a minimal band around provided price
            coerced_ranges = []
            for s in signals:
                price = float(s.price)
                # 0.2% minimal band
                buffer_ = max(price * 0.002, 1e-6)
                coerced_ranges.append({"min": max(0.0, price - buffer_), "max": price + buffer_, "weight": s.confidence * s.score})
            total_weight = sum(cr["weight"] for cr in coerced_ranges)
            if total_weight > 0:
                min_agg = sum((cr["min"] * cr["weight"]) for cr in coerced_ranges) / total_weight
                max_agg = sum((cr["max"] * cr["weight"]) for cr in coerced_ranges) / total_weight
                return {"min": min_agg, "max": max_agg}
            # Final fallback
            return {"min": 0.0, "max": 0.0}

        # Weight ranges by strategy confidence and score
        weighted_min = 0.0
        weighted_max = 0.0
        total_weight = 0.0

        for signal in valid_signals:
            weight = max(signal.confidence * signal.score, 1e-9)
            weighted_min += signal.entry_range['min'] * weight
            weighted_max += signal.entry_range['max'] * weight
            total_weight += weight

        if total_weight <= 0:
            return {"min": 0.0, "max": 0.0}

        agg = {"min": weighted_min / total_weight, "max": weighted_max / total_weight}
        # Ensure ordering and a minimal positive width
        if agg["max"] <= agg["min"]:
            delta = max((agg["min"] + agg["max"]) * 0.0005, 1e-6)
            agg["max"] = agg["min"] + delta
        return agg
    
    def _analyze_signals(self, signals: List[StrategySignal], data: Dict[str, pd.DataFrame]) -> RecommendationResult:
        """Analyze signals and generate final recommendation with improved neutral signal handling."""
        
        # Group signals by type
        buy_signals = [s for s in signals if s.signal == 1]
        sell_signals = [s for s in signals if s.signal == -1]
        hold_signals = [s for s in signals if s.signal == 0]
        
        # Calculate active vs neutral signal counts
        active_signals = buy_signals + sell_signals
        total_signals = len(signals)
        active_count = len(active_signals)
        hold_count = len(hold_signals)
        
        # Apply neutral signal weighting - heavily reduce influence when there are active signals
        if active_count > 0:
            # Weight neutral signals far less when active signals exist (max 5%)
            neutral_weight_factor = min(0.05, active_count / max(total_signals, 1))
            weighted_hold_count = hold_count * neutral_weight_factor
        else:
            # Only use neutrals if no active signals at all
            weighted_hold_count = hold_count
        
        # Calculate consensus with weighted neutrals
        effective_total = active_count + weighted_hold_count
        buy_ratio = len(buy_signals) / effective_total if effective_total > 0 else 0
        sell_ratio = len(sell_signals) / effective_total if effective_total > 0 else 0
        hold_ratio = weighted_hold_count / effective_total if effective_total > 0 else 0
        
        # Determine primary action with minimum confidence threshold
        min_confidence_threshold = 0.05  # Further reduced to 5% for more active signals
        
        if buy_ratio > sell_ratio and buy_ratio > hold_ratio and buy_ratio >= min_confidence_threshold:
            action = "BUY"
            primary_signals = buy_signals
        elif sell_ratio > buy_ratio and sell_ratio > hold_ratio and sell_ratio >= min_confidence_threshold:
            action = "SELL"
            primary_signals = sell_signals
        else:
            action = "HOLD"
            primary_signals = hold_signals
            
            # If no active signals, try to find the strongest recent signals
            if active_count == 0 and len(signals) > 0:
                # Find signals with highest confidence in the last 10 periods
                recent_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)[:3]
                if recent_signals and recent_signals[0].confidence > 0.05:
                    # Use the strongest recent signal as primary
                    strongest_signal = recent_signals[0]
                    if strongest_signal.signal == 1:
                        action = "BUY"
                        primary_signals = [strongest_signal]
                    elif strongest_signal.signal == -1:
                        action = "SELL"
                        primary_signals = [strongest_signal]
        
        # Calculate weighted confidence with enhanced scoring
        if primary_signals:
            # Enhanced confidence calculation considering signal strength and recency
            confidence_scores = []
            for s in primary_signals:
                # Base confidence from strategy
                base_conf = s.confidence * s.score
                # Boost for active signals vs neutrals
                signal_boost = 1.2 if s.signal != 0 else 0.8
                # Additional boost for high-strength signals
                strength_boost = 1.0 + (s.strength * 0.3)
                # Extra slight boost for strong recent (lower TF) signals
                recency_boost = 1.05 if (s.timeframe in ('1h', '4h') and s.strength >= 0.6 and s.signal != 0) else 1.0
                final_conf = base_conf * signal_boost * strength_boost * recency_boost
                confidence_scores.append(min(final_conf, 1.0))
            
            weighted_confidence = sum(confidence_scores) / len(confidence_scores)
            primary_strategy = max(primary_signals, key=lambda s: s.confidence * s.score).strategy_name
        else:
            # Fallback confidence calculation when no primary signals
            if len(signals) > 0:
                # Use average confidence of all signals with minimum threshold
                all_confidences = [s.confidence for s in signals if s.confidence > 0]
                if all_confidences:
                    weighted_confidence = max(sum(all_confidences) / len(all_confidences), 0.05)  # Minimum 5%
                else:
                    weighted_confidence = 0.05  # Minimum confidence
                primary_strategy = "Mixed"
            else:
                weighted_confidence = 0.05  # Minimum confidence
                primary_strategy = "None"
        
        # Historical score linkage and confidence floors
        def _mean(values: List[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        if primary_signals:
            avg_primary_score = _mean([s.score for s in primary_signals])
        else:
            # fallback to best available active/all signals
            source = active_signals if active_signals else signals
            top_scores = sorted([s.score for s in source], reverse=True)[:3]
            avg_primary_score = _mean(top_scores)

        # Add a capped historical boost (ties historical rank to instant confidence)
        historical_boost = min(max(avg_primary_score, 0.0) * 0.25, 0.25)
        weighted_confidence = min(1.0, weighted_confidence + historical_boost)

        # Apply action-specific minimum floors to avoid degradation to ~1%
        if primary_signals:
            supporting_count = len(primary_signals)
            avg_strength = _mean([s.strength for s in primary_signals])
            high_rank_present = any(s.score >= 0.7 for s in primary_signals)

            floor = 0.15 if (action in ("BUY", "SELL")) else 0.05
            if action in ("BUY", "SELL"):
                if supporting_count >= 2:
                    floor = max(floor, 0.30)
                if high_rank_present and avg_strength >= 0.4:
                    floor = max(floor, 0.25)
            else:  # HOLD
                # If there are high-ranked active signals in any TF, do not show near-zero
                if any((s.signal != 0 and s.score >= 0.7) for s in signals):
                    floor = max(floor, 0.10)

            weighted_confidence = max(weighted_confidence, floor)

        # Calculate signal consensus with active signal bias
        if active_count > 0:
            # When active signals exist, bias toward them more aggressively
            signal_consensus = max(buy_ratio, sell_ratio) * 2.0  # Increased boost for active signals
        else:
            signal_consensus = hold_ratio
        
        # Add timeframe analysis to strategy details
        timeframe_analysis = self._analyze_timeframe_contribution(signals)
        
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
            trade_management = aggregated_risk.trade_management
            
            # Final validation: ensure SL/TP are outside entry range
            if entry_range and 'min' in entry_range and 'max' in entry_range:
                stop_loss, take_profit = self._validate_levels_outside_entry_range(
                    stop_loss, take_profit, entry_range, current_price
                )
        else:
            current_price = 0.0
            entry_range = {"min": 0.0, "max": 0.0}
            stop_loss = 0.0
            take_profit = 0.0
            trade_management = None
        
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
        
        # Calculate contribution breakdown
        contribution_breakdown = self._calculate_contribution_breakdown(signals, entry_range, stop_loss, take_profit)

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
            risk_level=risk_level,
            trade_management=trade_management.__dict__ if trade_management else None,
            contribution_breakdown=contribution_breakdown
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
    
    def _validate_levels_outside_entry_range(self, stop_loss: float, take_profit: float, 
                                           entry_range: Dict[str, float], current_price: float) -> Tuple[float, float]:
        """
        Final validation to ensure SL/TP are outside entry range.
        This prevents degenerate levels where SL/TP collapse within the entry range.
        """
        if not entry_range or 'min' not in entry_range or 'max' not in entry_range:
            return stop_loss, take_profit
        
        entry_min = entry_range['min']
        entry_max = entry_range['max']
        
        # Calculate minimum distance from entry range (1% of current price)
        min_distance = current_price * 0.01
        
        # Ensure stop loss is outside entry range
        if stop_loss < current_price:  # Long position
            # Stop loss should be below entry range
            if stop_loss >= entry_min - min_distance:
                adjusted_stop_loss = entry_min - min_distance
            else:
                adjusted_stop_loss = stop_loss
        else:  # Short position
            # Stop loss should be above entry range
            if stop_loss <= entry_max + min_distance:
                adjusted_stop_loss = entry_max + min_distance
            else:
                adjusted_stop_loss = stop_loss
        
        # Ensure take profit is outside entry range
        if take_profit > current_price:  # Long position
            # Take profit should be above entry range
            if take_profit <= entry_max + min_distance:
                adjusted_take_profit = entry_max + min_distance
            else:
                adjusted_take_profit = take_profit
        else:  # Short position
            # Take profit should be below entry range
            if take_profit >= entry_min - min_distance:
                adjusted_take_profit = entry_min - min_distance
            else:
                adjusted_take_profit = take_profit
        
        return adjusted_stop_loss, adjusted_take_profit
    
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
    
    def _analyze_timeframe_contribution(self, signals: List[StrategySignal]) -> Dict[str, any]:
        """Analyze contribution of each timeframe to the final recommendation."""
        timeframe_stats = {}
        
        for signal in signals:
            tf = signal.timeframe
            if tf not in timeframe_stats:
                timeframe_stats[tf] = {
                    'total_signals': 0,
                    'active_signals': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'avg_confidence': 0.0,
                    'avg_strength': 0.0,
                    'total_confidence': 0.0,
                    'total_strength': 0.0
                }
            
            stats = timeframe_stats[tf]
            stats['total_signals'] += 1
            stats['total_confidence'] += signal.confidence
            stats['total_strength'] += signal.strength
            
            if signal.signal != 0:
                stats['active_signals'] += 1
                if signal.signal == 1:
                    stats['buy_signals'] += 1
                elif signal.signal == -1:
                    stats['sell_signals'] += 1
        
        # Calculate averages
        for tf, stats in timeframe_stats.items():
            if stats['total_signals'] > 0:
                stats['avg_confidence'] = stats['total_confidence'] / stats['total_signals']
                stats['avg_strength'] = stats['total_strength'] / stats['total_signals']
                stats['active_rate'] = stats['active_signals'] / stats['total_signals']
            else:
                stats['avg_confidence'] = 0.0
                stats['avg_strength'] = 0.0
                stats['active_rate'] = 0.0
        
        return timeframe_stats

    def _get_profile_weights(self, profile: str) -> Dict[str, float]:
        """Get timeframe weights based on trading profile."""
        profile_weights = {
            'day_trading': {
                '1h': 1.0,   # Highest weight for hourly (intraday focus)
                '4h': 0.8,   # High weight for 4-hour
                '1d': 0.4,   # Lower weight for daily
                '1w': 0.2    # Minimal weight for weekly
            },
            'swing': {
                '4h': 1.0,   # Highest weight for 4-hour (swing focus)
                '1d': 0.9,   # High weight for daily
                '1h': 0.6,   # Medium weight for hourly
                '1w': 0.3    # Lower weight for weekly
            },
            'balanced': {
                '1w': 1.0,   # Highest weight for weekly (most reliable)
                '1d': 0.9,   # High weight for daily
                '4h': 0.7,   # Medium-high weight for 4-hour
                '1h': 0.5    # Still lower than higher TFs, but not overly penalized
            },
            'long_term': {
                '1w': 1.0,   # Highest weight for weekly (long-term focus)
                '1d': 0.8,   # High weight for daily
                '4h': 0.4,   # Lower weight for 4-hour
                '1h': 0.2    # Minimal weight for hourly
            }
        }
        
        return profile_weights.get(profile, profile_weights['balanced'])

    def _calculate_contribution_breakdown(self, signals: List[StrategySignal], 
                                        entry_range: Dict[str, float], 
                                        stop_loss: float, 
                                        take_profit: float) -> List[ContributionBreakdown]:
        """Calculate detailed breakdown of how each strategy contributed to the recommendation."""
        if not signals:
            return []
        
        # Calculate total weight for normalization
        total_weight = sum(max(signal.confidence * signal.score, 1e-9) for signal in signals)
        
        breakdown = []
        for signal in signals:
            weight = max(signal.confidence * signal.score, 1e-9)
            weight_percentage = (weight / total_weight) * 100 if total_weight > 0 else 0
            
            # Calculate entry range contribution
            entry_contribution = {
                'min': signal.entry_range.get('min', 0) * weight_percentage / 100,
                'max': signal.entry_range.get('max', 0) * weight_percentage / 100
            }
            
            # Calculate SL/TP contribution (simplified - based on weight)
            sl_contribution = signal.risk_targets.get('stop_loss', 0) * weight_percentage / 100
            tp_contribution = signal.risk_targets.get('take_profit', 0) * weight_percentage / 100
            
            breakdown.append(ContributionBreakdown(
                strategy_name=signal.strategy_name,
                timeframe=signal.timeframe,
                signal=signal.signal,
                confidence=signal.confidence,
                strength=signal.strength,
                score=signal.score,
                weight=weight_percentage,
                entry_contribution=entry_contribution,
                sl_contribution=sl_contribution,
                tp_contribution=tp_contribution,
                reason=signal.reason
            ))
        
        # Sort by weight (highest contribution first)
        breakdown.sort(key=lambda x: x.weight, reverse=True)
        return breakdown


# Global service instance
recommendation_service = RecommendationService()
