"""Legacy simple aggregator (EXPERIMENTAL ONLY).

WARNING: Not supported in production. This simplified aggregator omits many
normalization and risk features present in the main service.
"""
from typing import List, Dict, Any


class RecommendationAggregator:
    """Aggregates signals from multiple strategies into a single recommendation.

    Notes on normalization and integrity:
    - No artificial confidence floors or boosts are applied. Confidence derives only from
      the weighted signal magnitude and is clamped to [0, 1].
    - Signal consensus is explicitly normalized to [0, 1] and capped to avoid duplication or >1.0.
    """

    def __init__(self):
        pass

    def generate_recommendation(self, strategies: List[Dict], signals: List[Dict]) -> Dict[str, Any]:
        if not strategies or not signals:
            return {"action": "FLAT", "confidence": 0.0, "entry_range": None, "stop_loss": None, "take_profit": None}

        weighted_signal = 0.0
        total_weight = 0.0

        for strategy in strategies:
            strategy_name = strategy.get('strategy_name', '')
            score = strategy.get('score', 0)
            signal = next((s for s in signals if s.get('strategy_name') == strategy_name), None)
            if signal and score > 0:
                signal_value = signal.get('signal', 0)
                weighted_signal += signal_value * score
                total_weight += score

        ratio = (weighted_signal / total_weight) if total_weight > 0 else 0.0

        if total_weight == 0:
            action = "FLAT"
            confidence = 0.0
        elif ratio > 0.5:
            action = "LONG"
            confidence = max(0.0, min(abs(ratio), 1.0))
        elif ratio < -0.5:
            action = "SHORT"
            confidence = max(0.0, min(abs(ratio), 1.0))
        else:
            action = "FLAT"
            confidence = max(0.0, min(abs(ratio), 1.0))

        current_price = signals[0].get('current_price', 0) if signals else 0
        entry_range = self._calculate_entry_range(signals, current_price)
        stop_loss = self._calculate_stop_loss(action, current_price)
        take_profit = self._calculate_take_profit(action, current_price)

        buys = sum(1 for s in signals if s.get('signal', 0) == 1)
        sells = sum(1 for s in signals if s.get('signal', 0) == -1)
        holds = sum(1 for s in signals if s.get('signal', 0) == 0)
        total = max(1, buys + sells + holds)
        majority = max(buys, sells, holds)
        signal_consensus = min(max(majority / total, 0.0), 1.0)

        return {
            "action": action,
            "confidence": confidence,
            "entry_range": entry_range,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "current_price": current_price,
            "signal_consensus": signal_consensus
        }

    def _calculate_entry_range(self, signals: List[Dict], current_price: float) -> Dict[str, float]:
        if not signals or current_price == 0:
            return {"min": current_price, "max": current_price}
        prices = [s.get('current_price', current_price) for s in signals]
        return {"min": min(prices), "max": max(prices)}

    def _calculate_stop_loss(self, action: str, entry_price: float) -> float:
        if action == "LONG":
            return entry_price * 0.98
        elif action == "SHORT":
            return entry_price * 1.02
        return entry_price

    def _calculate_take_profit(self, action: str, entry_price: float) -> float:
        if action == "LONG":
            return entry_price * 1.04
        elif action == "SHORT":
            return entry_price * 0.96
        return entry_price


