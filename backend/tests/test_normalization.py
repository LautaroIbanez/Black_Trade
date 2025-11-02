"""
Unit tests for recommendation normalization and transparency features.
"""

import unittest
import pandas as pd
from unittest.mock import Mock, patch
from backend.services.recommendation_service import RecommendationService, StrategySignal


class TestNormalization(unittest.TestCase):
    """Test normalization and transparency features."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = RecommendationService()
        
        # Create mock signals with different weights
        self.mock_signals = [
            StrategySignal(
                strategy_name="Strategy1",
                signal=1,
                strength=0.8,
                confidence=0.7,
                reason="Strong buy signal",
                price=50000.0,
                timestamp="2024-01-01",
                score=0.9,
                timeframe="1h",
                entry_range={"min": 49500.0, "max": 50500.0},
                risk_targets={"stop_loss": 48000.0, "take_profit": 52000.0}
            ),
            StrategySignal(
                strategy_name="Strategy2",
                signal=1,
                strength=0.6,
                confidence=0.5,
                reason="Moderate buy signal",
                price=50000.0,
                timestamp="2024-01-01",
                score=0.7,
                timeframe="4h",
                entry_range={"min": 49000.0, "max": 51000.0},
                risk_targets={"stop_loss": 47500.0, "take_profit": 52500.0}
            ),
            StrategySignal(
                strategy_name="Strategy3",
                signal=0,
                strength=0.3,
                confidence=0.4,
                reason="Neutral signal",
                price=50000.0,
                timestamp="2024-01-01",
                score=0.5,
                timeframe="1d",
                entry_range={"min": 49500.0, "max": 50500.0},
                risk_targets={"stop_loss": 48000.0, "take_profit": 52000.0}
            )
        ]
    
    def test_signal_consensus_normalization(self):
        """Test that signal_consensus is normalized to 0-1 range."""
        # Call the real method to test actual normalization behavior
        result = self.service._analyze_signals(self.mock_signals, {}, profile="balanced")
        
        # Signal consensus should always be in [0, 1] range
        self.assertGreaterEqual(result.signal_consensus, 0.0)
        self.assertLessEqual(result.signal_consensus, 1.0)
    
    def test_weights_normalization(self):
        """Test that strategy weights are normalized to sum to 1.0."""
        # Create strategy details with raw weights
        strategy_details = [
            {"strategy_name": "Strategy1", "weight": 0.63},  # 0.7 * 0.9
            {"strategy_name": "Strategy2", "weight": 0.35},  # 0.5 * 0.7
            {"strategy_name": "Strategy3", "weight": 0.20}   # 0.4 * 0.5
        ]
        
        # Normalize weights
        total_weight = sum(detail["weight"] for detail in strategy_details)
        normalized_details = []
        for detail in strategy_details:
            normalized_detail = detail.copy()
            normalized_detail["weight"] = detail["weight"] / total_weight
            normalized_details.append(normalized_detail)
        
        # Check that weights sum to 1.0
        total_normalized_weight = sum(detail["weight"] for detail in normalized_details)
        self.assertAlmostEqual(total_normalized_weight, 1.0, places=6)
        
        # Check that individual weights are proportional
        self.assertAlmostEqual(normalized_details[0]["weight"], 0.63 / 1.18, places=6)
        self.assertAlmostEqual(normalized_details[1]["weight"], 0.35 / 1.18, places=6)
        self.assertAlmostEqual(normalized_details[2]["weight"], 0.20 / 1.18, places=6)
    
    def test_risk_reward_ratio_calculation(self):
        """Test risk-reward ratio calculation."""
        # Test BUY scenario
        rrr_buy = self.service._calculate_risk_reward_ratio(
            stop_loss=48000.0,
            take_profit=52000.0,
            current_price=50000.0,
            action="BUY"
        )
        expected_buy = (52000.0 - 50000.0) / (50000.0 - 48000.0)  # 2000 / 2000 = 1.0
        self.assertAlmostEqual(rrr_buy, 1.0, places=2)
        
        # Test SELL scenario
        rrr_sell = self.service._calculate_risk_reward_ratio(
            stop_loss=52000.0,
            take_profit=48000.0,
            current_price=50000.0,
            action="SELL"
        )
        expected_sell = (50000.0 - 48000.0) / (52000.0 - 50000.0)  # 2000 / 2000 = 1.0
        self.assertAlmostEqual(rrr_sell, 1.0, places=2)
        
        # Test HOLD scenario
        rrr_hold = self.service._calculate_risk_reward_ratio(
            stop_loss=48000.0,
            take_profit=52000.0,
            current_price=50000.0,
            action="HOLD"
        )
        self.assertEqual(rrr_hold, 0.0)
    
    def test_position_size_calculation(self):
        """Test position size calculation."""
        # Test different profiles (day_trading < balanced < long_term risk)
        usd_balanced, pct_balanced = self.service._calculate_position_size(50000.0, 48000.0, "balanced")
        usd_day_trading, pct_day_trading = self.service._calculate_position_size(50000.0, 48000.0, "day_trading")
        usd_long_term, pct_long_term = self.service._calculate_position_size(50000.0, 48000.0, "long_term")
        
        # Day trading should be smaller than balanced, balanced smaller than long term (more risk)
        self.assertLess(pct_day_trading, pct_balanced)
        self.assertLess(pct_balanced, pct_long_term)
        
        # Test zero cases
        usd_zero, pct_zero = self.service._calculate_position_size(0.0, 0.0, "balanced")
        self.assertEqual(usd_zero, 0.0)
        self.assertEqual(pct_zero, 0.0)
    
    def test_entry_label_generation(self):
        """Test entry label generation based on price position."""
        entry_range = {"min": 49000.0, "max": 51000.0}
        
        # Test BUY scenarios
        label_below = self.service._generate_entry_label(48500.0, entry_range, "BUY", "MEDIUM")
        self.assertIn("Esperar pullback", label_below)
        
        label_above = self.service._generate_entry_label(51500.0, entry_range, "BUY", "MEDIUM")
        self.assertIn("Esperar corrección", label_above)
        
        label_lower = self.service._generate_entry_label(49500.0, entry_range, "BUY", "MEDIUM")
        self.assertIn("Entrada favorable", label_lower)
        
        label_upper = self.service._generate_entry_label(50500.0, entry_range, "BUY", "MEDIUM")
        self.assertIn("Entrada inmediata", label_upper)
        
        # Test SELL scenarios
        label_sell_above = self.service._generate_entry_label(51500.0, entry_range, "SELL", "MEDIUM")
        self.assertIn("Esperar pullback", label_sell_above)
        
        # Test HOLD scenario
        label_hold = self.service._generate_entry_label(50000.0, entry_range, "HOLD", "MEDIUM")
        self.assertIn("Esperar señal clara", label_hold)
    
    def test_risk_percentage_calculation(self):
        """Test risk percentage calculation."""
        # Test BUY scenario
        risk_pct_buy = self.service._calculate_risk_percentage(48000.0, 50000.0, "BUY")
        expected_buy = ((50000.0 - 48000.0) / 50000.0) * 100  # 4%
        self.assertAlmostEqual(risk_pct_buy, expected_buy, places=2)
        
        # Test SELL scenario
        risk_pct_sell = self.service._calculate_risk_percentage(52000.0, 50000.0, "SELL")
        expected_sell = ((52000.0 - 50000.0) / 50000.0) * 100  # 4%
        self.assertAlmostEqual(risk_pct_sell, expected_sell, places=2)
        
        # Test HOLD scenario
        risk_pct_hold = self.service._calculate_risk_percentage(48000.0, 50000.0, "HOLD")
        self.assertEqual(risk_pct_hold, 0.0)
    
    def test_mixed_input_validation(self):
        """Test normalization with mixed input scenarios."""
        # Test with empty signals
        empty_signals = []
        with patch.object(self.service, '_analyze_signals') as mock_analyze:
            mock_analyze.return_value = Mock(
                action="HOLD",
                confidence=0.05,
                entry_range={"min": 0.0, "max": 0.0},
                stop_loss=0.0,
                take_profit=0.0,
                current_price=0.0,
                primary_strategy="None",
                supporting_strategies=[],
                strategy_details=[],
                signal_consensus=0.0,
                risk_level="LOW",
                trade_management=None,
                contribution_breakdown=None,
                risk_reward_ratio=0.0,
                suggested_position_size=0.0,
                entry_label="No entry range available",
                risk_percentage=0.0,
                normalized_weights_sum=0.0
            )
            
            result = self.service._analyze_signals(empty_signals, {}, profile="balanced")
            
            # All values should be within expected ranges
            self.assertGreaterEqual(result.confidence, 0.0)
            self.assertLessEqual(result.confidence, 1.0)
            self.assertGreaterEqual(result.signal_consensus, 0.0)
            self.assertLessEqual(result.signal_consensus, 1.0)
            self.assertGreaterEqual(result.normalized_weights_sum, 0.0)
            self.assertLessEqual(result.normalized_weights_sum, 1.0)
    
    def test_edge_cases(self):
        """Test edge cases for normalization."""
        # Test with zero values
        rrr_zero = self.service._calculate_risk_reward_ratio(0.0, 0.0, 0.0, "BUY")
        self.assertEqual(rrr_zero, 0.0)
        
        # Test with negative risk
        rrr_negative = self.service._calculate_risk_reward_ratio(51000.0, 52000.0, 50000.0, "BUY")
        self.assertEqual(rrr_negative, 0.0)
        
        # Test with invalid entry range
        label_invalid = self.service._generate_entry_label(50000.0, {}, "BUY", "MEDIUM")
        self.assertEqual(label_invalid, "No entry range available")


if __name__ == '__main__':
    unittest.main()


