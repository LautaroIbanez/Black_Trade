"""Recommendation aggregator for combining strategy signals."""
from typing import List, Dict, Any
import pandas as pd


class RecommendationAggregator:
    """Aggregates signals from multiple strategies into a single recommendation."""
    
    def __init__(self):
        """Initialize aggregator."""
        pass
    
    def generate_recommendation(self, strategies: List[Dict], signals: List[Dict]) -> Dict[str, Any]:
        """Generate combined recommendation from strategies and signals."""
        if not strategies or not signals:
            return {"action": "FLAT", "confidence": 0.0, "entry_range": None, "stop_loss": None, "take_profit": None}
        
        # Weight signals by strategy score
        weighted_signal = 0.0
        total_weight = 0.0
        
        for strategy in strategies:
            strategy_name = strategy.get('strategy_name', '')
            score = strategy.get('score', 0)
            
            # Find matching signal
            signal = next((s for s in signals if s.get('strategy_name') == strategy_name), None)
            if signal and score > 0:
                signal_value = signal.get('signal', 0)
                weighted_signal += signal_value * score
                total_weight += score
        
        if total_weight == 0:
            action = "FLAT"
            confidence = 0.0
        elif weighted_signal / total_weight > 0.5:
            action = "LONG"
            confidence = min(abs(weighted_signal / total_weight), 1.0)
        elif weighted_signal / total_weight < -0.5:
            action = "SHORT"
            confidence = min(abs(weighted_signal / total_weight), 1.0)
        else:
            action = "FLAT"
            confidence = 0.3
        
        # Calculate entry range, SL, TP from signals
        current_price = signals[0].get('current_price', 0) if signals else 0
        entry_range = self._calculate_entry_range(signals, current_price)
        stop_loss = self._calculate_stop_loss(action, current_price)
        take_profit = self._calculate_take_profit(action, current_price)
        
        return {
            "action": action,
            "confidence": confidence,
            "entry_range": entry_range,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "current_price": current_price
        }
    
    def _calculate_entry_range(self, signals: List[Dict], current_price: float) -> Dict[str, float]:
        """Calculate entry price range."""
        if not signals or current_price == 0:
            return {"min": current_price, "max": current_price}
        
        prices = [s.get('current_price', current_price) for s in signals]
        return {"min": min(prices), "max": max(prices)}
    
    def _calculate_stop_loss(self, action: str, entry_price: float) -> float:
        """Calculate stop loss level."""
        if action == "LONG":
            return entry_price * 0.98
        elif action == "SHORT":
            return entry_price * 1.02
        return entry_price
    
    def _calculate_take_profit(self, action: str, entry_price: float) -> float:
        """Calculate take profit level."""
        if action == "LONG":
            return entry_price * 1.04
        elif action == "SHORT":
            return entry_price * 0.96
        return entry_price

