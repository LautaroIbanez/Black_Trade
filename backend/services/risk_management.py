"""
Risk Management Service.

This service combines individual strategy risk targets to produce aggregated
stop loss and take profit levels, considering support/resistance zones and
market volatility.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from backtest.indicators.support_resistance import (
    SupportResistanceDetector, 
    SupportResistanceLevel,
    calculate_support_resistance_levels
)


@dataclass
class RiskTarget:
    """Represents a risk target from a single strategy."""
    strategy_name: str
    stop_loss: float
    take_profit: float
    confidence: float
    strength: float
    timeframe: str


@dataclass
class TradeManagement:
    """Trade management information for active positions."""
    entry_price: float
    stop_loss: float
    take_profit: float
    current_price: float
    unrealized_pnl: float
    risk_reward_ratio: float
    max_risk_pct: float
    potential_reward_pct: float
    strategy_name: str
    signal_strength: float
    confidence: float
    timeframe: str
    status: str  # "OPEN", "HIT_SL", "HIT_TP", "MANUAL_CLOSE"
    entry_time: str
    last_updated: str

@dataclass
class AggregatedRiskTargets:
    """Aggregated risk targets from multiple strategies."""
    stop_loss: float
    take_profit: float
    confidence: float
    risk_reward_ratio: float
    strategy_contributions: List[Dict[str, any]]
    support_resistance_analysis: Dict[str, any]
    trade_management: Optional[TradeManagement] = None


class RiskManagementService:
    """Service for managing risk targets across multiple strategies."""
    
    def __init__(self):
        """Initialize the risk management service."""
        self.support_resistance_detector = SupportResistanceDetector()
        self.risk_levels = {
            "LOW": {"max_risk": 0.02, "min_reward": 0.04},
            "MEDIUM": {"max_risk": 0.03, "min_reward": 0.06},
            "HIGH": {"max_risk": 0.05, "min_reward": 0.10}
        }
    
    def aggregate_risk_targets(self, risk_targets: List[RiskTarget], 
                             historical_data: Optional[Dict[str, pd.DataFrame]] = None,
                             current_price: float = 0.0,
                             risk_profile: str = "balanced") -> AggregatedRiskTargets:
        """
        Aggregate risk targets from multiple strategies.
        
        Args:
            risk_targets: List of risk targets from individual strategies
            historical_data: Historical data for support/resistance analysis
            current_price: Current market price
            
        Returns:
            AggregatedRiskTargets object
        """
        if not risk_targets:
            return self._create_default_risk_targets(current_price)
        
        # Calculate weighted averages
        weighted_stop_loss, weighted_take_profit, total_weight = self._calculate_weighted_levels(risk_targets)
        
        # Analyze support/resistance levels
        sr_analysis = self._analyze_support_resistance(historical_data, current_price)
        
        # ATR-based minimum distances by profile
        atr_value = self._estimate_atr(historical_data)
        profile_cfg = self._get_profile_risk_config(risk_profile)
        min_sl_distance = 0.0
        min_tp_rr = profile_cfg.get('min_rr', 1.5)
        if atr_value and current_price:
            min_sl_distance = atr_value * profile_cfg.get('sl_atr_mult', 1.2)
        
        # Enforce ATR-based minimum SL/TP distances
        adjusted_stop_loss, adjusted_take_profit = self._enforce_atr_minimums(
            weighted_stop_loss, weighted_take_profit, current_price, min_sl_distance, min_tp_rr
        )
        
        # Adjust levels based on support/resistance
        adjusted_stop_loss, adjusted_take_profit = self._adjust_for_support_resistance(
            adjusted_stop_loss, adjusted_take_profit, sr_analysis, current_price
        )
        
        # Ensure levels are outside entry range to prevent degeneration
        if historical_data:
            # Get entry range from the highest timeframe available
            # Priority: 1w > 1d > 4h > 1h (higher timeframes have more reliable ranges)
            preferred_timeframes = ['1w', '1d', '4h', '1h']
            selected_timeframe = None
            
            for tf in preferred_timeframes:
                if tf in historical_data and not historical_data[tf].empty:
                    selected_timeframe = tf
                    break
            
            if not selected_timeframe:
                # Fallback to any available timeframe
                selected_timeframe = max(historical_data.keys())
            
            df = historical_data[selected_timeframe]
            if not df.empty:
                # Calculate entry range using the first strategy as reference
                if risk_targets:
                    # Use a simple approach: calculate entry range from current price
                    entry_range = self._calculate_entry_range_from_price(current_price, df)
                    adjusted_stop_loss, adjusted_take_profit = self._ensure_levels_outside_entry_range(
                        adjusted_stop_loss, adjusted_take_profit, entry_range, current_price,
                        atr_value=atr_value, profile=risk_profile
                    )
        
        # Calculate risk metrics
        risk_reward_ratio = self._calculate_risk_reward_ratio(adjusted_stop_loss, adjusted_take_profit, current_price)
        confidence = self._calculate_aggregated_confidence(risk_targets)
        
        # Prepare strategy contributions
        strategy_contributions = self._prepare_strategy_contributions(risk_targets)
        
        # Create trade management information if we have active signals
        trade_management = None
        if risk_targets and current_price > 0:
            trade_management = self._create_trade_management(
                risk_targets, adjusted_stop_loss, adjusted_take_profit, 
                current_price, confidence
            )
        
        return AggregatedRiskTargets(
            stop_loss=adjusted_stop_loss,
            take_profit=adjusted_take_profit,
            confidence=confidence,
            risk_reward_ratio=risk_reward_ratio,
            strategy_contributions=strategy_contributions,
            support_resistance_analysis=sr_analysis,
            trade_management=trade_management
        )

    def _estimate_atr(self, historical_data: Optional[Dict[str, pd.DataFrame]]) -> Optional[float]:
        """Estimate ATR(14) from the highest-available timeframe data."""
        if not historical_data:
            return None
        # Prefer higher TF for stability
        for tf in ['1w', '1d', '4h', '2h', '1h', '12h']:
            df = historical_data.get(tf)
            if df is not None and not df.empty and all(k in df.columns for k in ['high','low','close']):
                high_low = df['high'] - df['low']
                high_close = (df['high'] - df['close'].shift()).abs()
                low_close = (df['low'] - df['close'].shift()).abs()
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()
                val = float(atr.iloc[-1]) if not atr.empty else None
                if val and val > 0:
                    return val
        return None

    def _get_profile_risk_config(self, profile: str) -> Dict[str, float]:
        """Risk profile configuration for ATR multipliers and target RR."""
        profile = (profile or "balanced").lower()
        mapping = {
            "day_trading": {"sl_atr_mult": 1.0, "min_rr": 1.5, "entry_buffer_atr_mult": 0.6},
            "swing": {"sl_atr_mult": 1.5, "min_rr": 2.0, "entry_buffer_atr_mult": 0.8},
            "balanced": {"sl_atr_mult": 1.2, "min_rr": 1.8, "entry_buffer_atr_mult": 0.7},
            "long_term": {"sl_atr_mult": 2.0, "min_rr": 2.5, "entry_buffer_atr_mult": 1.0},
        }
        return mapping.get(profile, mapping["balanced"])

    def _enforce_atr_minimums(self, sl: float, tp: float, price: float, min_sl_distance: float, min_rr: float) -> Tuple[float, float]:
        """Ensure SL is at least min distance away, and TP targets at least min RR."""
        if price <= 0:
            return sl, tp
        adjusted_sl = sl
        adjusted_tp = tp
        if min_sl_distance and min_sl_distance > 0:
            # Determine side by comparing sl to price
            if sl < price:
                # long
                target_sl = price - min_sl_distance
                if adjusted_sl > target_sl:
                    adjusted_sl = target_sl
                # TP should meet RR
                rr_tp = price + min_rr * (price - adjusted_sl)
                if adjusted_tp < rr_tp:
                    adjusted_tp = rr_tp
            elif sl > price:
                # short
                target_sl = price + min_sl_distance
                if adjusted_sl < target_sl:
                    adjusted_sl = target_sl
                rr_tp = price - min_rr * (adjusted_sl - price)
                if adjusted_tp > rr_tp:
                    adjusted_tp = rr_tp
        return adjusted_sl, adjusted_tp
    
    def _calculate_weighted_levels(self, risk_targets: List[RiskTarget]) -> Tuple[float, float, float]:
        """Calculate weighted stop loss and take profit levels."""
        weighted_stop_loss = 0.0
        weighted_take_profit = 0.0
        total_weight = 0.0
        
        for target in risk_targets:
            # Weight by confidence and strength
            weight = target.confidence * target.strength
            weighted_stop_loss += target.stop_loss * weight
            weighted_take_profit += target.take_profit * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_stop_loss / total_weight, weighted_take_profit / total_weight, total_weight
        else:
            # Fallback to simple average
            stop_losses = [t.stop_loss for t in risk_targets]
            take_profits = [t.take_profit for t in risk_targets]
            return np.mean(stop_losses), np.mean(take_profits), len(risk_targets)
    
    def _analyze_support_resistance(self, historical_data: Optional[Dict[str, pd.DataFrame]], 
                                   current_price: float) -> Dict[str, any]:
        """Analyze support and resistance levels from historical data."""
        if not historical_data:
            return {"levels": [], "nearest_support": None, "nearest_resistance": None}
        
        # Use the highest timeframe available for support/resistance analysis
        # Priority: 1w > 1d > 4h > 1h (higher timeframes have more reliable levels)
        preferred_timeframes = ['1w', '1d', '4h', '1h']
        selected_timeframe = None
        
        for tf in preferred_timeframes:
            if tf in historical_data and not historical_data[tf].empty:
                selected_timeframe = tf
                break
        
        if not selected_timeframe:
            # Fallback to any available timeframe
            selected_timeframe = max(historical_data.keys())
        
        df = historical_data[selected_timeframe]
        
        if df.empty:
            return {"levels": [], "nearest_support": None, "nearest_resistance": None}
        
        # Detect support/resistance levels
        levels = self.support_resistance_detector.detect_levels(df)
        
        # Get relevant levels near current price
        relevant_levels = self.support_resistance_detector.get_relevant_levels(
            levels, current_price, price_range=0.15  # 15% range
        )
        
        # Find nearest support and resistance
        support_levels = [l for l in relevant_levels if l.level_type == 'support' and l.price < current_price]
        resistance_levels = [l for l in relevant_levels if l.level_type == 'resistance' and l.price > current_price]
        
        nearest_support = max(support_levels, key=lambda x: x.price) if support_levels else None
        nearest_resistance = min(resistance_levels, key=lambda x: x.price) if resistance_levels else None
        
        return {
            "levels": relevant_levels,
            "nearest_support": nearest_support,
            "nearest_resistance": nearest_resistance,
            "total_levels": len(levels),
            "relevant_levels": len(relevant_levels)
        }
    
    def _adjust_for_support_resistance(self, stop_loss: float, take_profit: float,
                                     sr_analysis: Dict[str, any], current_price: float) -> Tuple[float, float]:
        """Adjust risk levels based on support/resistance analysis."""
        adjusted_stop_loss = stop_loss
        adjusted_take_profit = take_profit
        
        nearest_support = sr_analysis.get("nearest_support")
        nearest_resistance = sr_analysis.get("nearest_resistance")
        
        # Adjust stop loss to avoid strong support/resistance levels
        if nearest_support and stop_loss < current_price:
            # For long positions, ensure stop loss is below support
            if stop_loss > nearest_support.price * 0.98:  # 2% below support
                adjusted_stop_loss = nearest_support.price * 0.95  # 5% below support
        
        if nearest_resistance and stop_loss > current_price:
            # For short positions, ensure stop loss is above resistance
            if stop_loss < nearest_resistance.price * 1.02:  # 2% above resistance
                adjusted_stop_loss = nearest_resistance.price * 1.05  # 5% above resistance
        
        # Adjust take profit to target resistance levels
        if nearest_resistance and take_profit > current_price:
            # For long positions, consider resistance as take profit target
            if take_profit > nearest_resistance.price * 1.1:  # Too far above resistance
                adjusted_take_profit = nearest_resistance.price * 0.98  # Just below resistance
        
        if nearest_support and take_profit < current_price:
            # For short positions, consider support as take profit target
            if take_profit < nearest_support.price * 0.9:  # Too far below support
                adjusted_take_profit = nearest_support.price * 1.02  # Just above support
        
        return adjusted_stop_loss, adjusted_take_profit
    
    def _ensure_levels_outside_entry_range(self, stop_loss: float, take_profit: float, 
                                         entry_range: Dict[str, float], current_price: float,
                                         atr_value: Optional[float] = None, profile: str = "balanced") -> Tuple[float, float]:
        """
        Ensure stop loss and take profit levels are outside the entry range.
        Buffer distance is dynamic: derived from ATR and profile config when available.
        Falls back to a small percentage only if ATR is unavailable.
        """
        if not entry_range or 'min' not in entry_range or 'max' not in entry_range:
            return stop_loss, take_profit
        
        entry_min = entry_range['min']
        entry_max = entry_range['max']

        # Dynamic buffer: prefer ATR-based distance, else fallback to small pct
        cfg = self._get_profile_risk_config(profile)
        entry_buf_mult = float(cfg.get('entry_buffer_atr_mult', 0.7))
        if atr_value and atr_value > 0 and current_price > 0:
            min_distance = max(atr_value * entry_buf_mult, 1e-9)
        else:
            # Fallback buffer as 0.5% of price when ATR is unavailable
            min_distance = current_price * 0.005
        
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
    
    def _calculate_entry_range_from_price(self, current_price: float, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate a basic entry range from current price using volatility.
        Used as fallback when strategy-specific entry ranges are not available.
        """
        # Calculate ATR for volatility-based range
        atr = self._calculate_atr(df, 14)
        atr_value = float(atr.iloc[-1]) if not atr.empty else current_price * 0.01
        
        # Calculate standard deviation for additional volatility measure
        if len(df) >= 20:
            price_std = df['close'].rolling(window=20).std().iloc[-1]
            if not pd.isna(price_std):
                std_value = float(price_std)
            else:
                std_value = current_price * 0.01
        else:
            std_value = current_price * 0.01
        
        # Use the larger of ATR or standard deviation for range calculation
        volatility_measure = max(atr_value, std_value)
        
        # Ensure minimum range width (0.5% of current price)
        min_range_width = current_price * 0.005
        range_width = max(volatility_measure * 0.5, min_range_width)
        
        # Create symmetric range around current price
        min_price = current_price - range_width
        max_price = current_price + range_width
        
        return {
            "min": max(0.0, min_price),  # Ensure non-negative
            "max": max_price
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def _calculate_risk_reward_ratio(self, stop_loss: float, take_profit: float, current_price: float) -> float:
        """Calculate risk-reward ratio."""
        if stop_loss == current_price or take_profit == current_price:
            return 0.0
        
        # Calculate potential loss and gain
        if stop_loss < current_price:  # Long position
            potential_loss = current_price - stop_loss
            potential_gain = take_profit - current_price
        else:  # Short position
            potential_loss = stop_loss - current_price
            potential_gain = current_price - take_profit
        
        if potential_loss <= 0:
            return 0.0
        
        return potential_gain / potential_loss
    
    def _calculate_aggregated_confidence(self, risk_targets: List[RiskTarget]) -> float:
        """Calculate aggregated confidence from all risk targets."""
        if not risk_targets:
            return 0.0
        
        # Weight by strategy strength
        weighted_confidence = sum(t.confidence * t.strength for t in risk_targets)
        total_weight = sum(t.strength for t in risk_targets)
        
        if total_weight > 0:
            return min(weighted_confidence / total_weight, 1.0)
        else:
            return np.mean([t.confidence for t in risk_targets])
    
    def _prepare_strategy_contributions(self, risk_targets: List[RiskTarget]) -> List[Dict[str, any]]:
        """Prepare strategy contribution details."""
        contributions = []
        
        for target in risk_targets:
            contributions.append({
                "strategy_name": target.strategy_name,
                "stop_loss": target.stop_loss,
                "take_profit": target.take_profit,
                "confidence": target.confidence,
                "strength": target.strength,
                "timeframe": target.timeframe,
                "weight": target.confidence * target.strength
            })
        
        # Sort by weight
        contributions.sort(key=lambda x: x["weight"], reverse=True)
        
        return contributions
    
    def _create_default_risk_targets(self, current_price: float) -> AggregatedRiskTargets:
        """Create default risk targets when no strategy targets are available."""
        return AggregatedRiskTargets(
            stop_loss=current_price * 0.98,  # 2% stop loss
            take_profit=current_price * 1.04,  # 4% take profit
            confidence=0.0,
            risk_reward_ratio=2.0,
            strategy_contributions=[],
            support_resistance_analysis={"levels": [], "nearest_support": None, "nearest_resistance": None}
        )
    
    def validate_risk_levels(self, stop_loss: float, take_profit: float, 
                           current_price: float, risk_level: str = "MEDIUM") -> Dict[str, any]:
        """
        Validate risk levels against risk management rules.
        
        Args:
            stop_loss: Stop loss level
            take_profit: Take profit level
            current_price: Current market price
            risk_level: Risk level (LOW, MEDIUM, HIGH)
            
        Returns:
            Validation results
        """
        if risk_level not in self.risk_levels:
            risk_level = "MEDIUM"
        
        risk_config = self.risk_levels[risk_level]
        max_risk = risk_config["max_risk"]
        min_reward = risk_config["min_reward"]
        
        # Calculate actual risk and reward
        if stop_loss < current_price:  # Long position
            actual_risk = (current_price - stop_loss) / current_price
            actual_reward = (take_profit - current_price) / current_price
        else:  # Short position
            actual_risk = (stop_loss - current_price) / current_price
            actual_reward = (current_price - take_profit) / current_price
        
        # Validation results
        risk_valid = actual_risk <= max_risk
        reward_valid = actual_reward >= min_reward
        ratio_valid = actual_reward / actual_risk >= 1.5 if actual_risk > 0 else False
        
        return {
            "valid": risk_valid and reward_valid and ratio_valid,
            "risk_valid": risk_valid,
            "reward_valid": reward_valid,
            "ratio_valid": ratio_valid,
            "actual_risk": actual_risk,
            "actual_reward": actual_reward,
            "risk_reward_ratio": actual_reward / actual_risk if actual_risk > 0 else 0,
            "max_allowed_risk": max_risk,
            "min_required_reward": min_reward
        }
    
    def _create_trade_management(self, risk_targets: List[RiskTarget], 
                               stop_loss: float, take_profit: float, 
                               current_price: float, confidence: float) -> TradeManagement:
        """Create trade management information for active positions."""
        from datetime import datetime
        
        # Use the highest confidence strategy as primary
        primary_strategy = max(risk_targets, key=lambda x: x.confidence)
        
        # Calculate entry price (use current price as entry for new positions)
        entry_price = current_price
        
        # Calculate unrealized PnL (assuming we're in a position)
        # This would need to be tracked separately in a real system
        unrealized_pnl = 0.0  # Placeholder - would need actual position tracking
        
        # Calculate risk/reward ratios
        if stop_loss != current_price and take_profit != current_price:
            risk_amount = abs(current_price - stop_loss)
            reward_amount = abs(take_profit - current_price)
            risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0.0
        else:
            risk_reward_ratio = 0.0
        
        # Calculate percentage risks
        max_risk_pct = abs(current_price - stop_loss) / current_price * 100 if current_price > 0 else 0
        potential_reward_pct = abs(take_profit - current_price) / current_price * 100 if current_price > 0 else 0
        
        return TradeManagement(
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            risk_reward_ratio=risk_reward_ratio,
            max_risk_pct=max_risk_pct,
            potential_reward_pct=potential_reward_pct,
            strategy_name=primary_strategy.strategy_name,
            signal_strength=primary_strategy.strength,
            confidence=confidence,
            timeframe=primary_strategy.timeframe,
            status="OPEN",
            entry_time=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )


# Global instance
risk_management_service = RiskManagementService()
