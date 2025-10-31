"""
Tests for risk management system.
"""

import unittest
import pandas as pd
import numpy as np
from backend.services.risk_management import (
    RiskManagementService, 
    RiskTarget, 
    AggregatedRiskTargets,
    SupportResistanceDetector,
    SupportResistanceLevel
)
from backtest.indicators.support_resistance import calculate_support_resistance_levels
from backend.services.recommendation_service import RecommendationService, StrategySignal


class TestRiskManagementService(unittest.TestCase):
    """Test risk management service functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.risk_service = RiskManagementService()
        
        # Create sample OHLCV data
        dates = pd.date_range('2024-01-01', periods=100, freq='1H')
        np.random.seed(42)
        
        # Generate realistic price data
        base_price = 50000
        price_changes = np.random.normal(0, 0.02, 100)
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Create sample risk targets
        self.risk_targets = [
            RiskTarget(
                strategy_name="EMA_RSI",
                stop_loss=49000.0,
                take_profit=52000.0,
                confidence=0.8,
                strength=0.9,
                timeframe="1h"
            ),
            RiskTarget(
                strategy_name="Momentum",
                stop_loss=48500.0,
                take_profit=52500.0,
                confidence=0.7,
                strength=0.8,
                timeframe="4h"
            ),
            RiskTarget(
                strategy_name="Breakout",
                stop_loss=49500.0,
                take_profit=51500.0,
                confidence=0.9,
                strength=0.7,
                timeframe="1h"
            )
        ]
    
    def test_aggregate_risk_targets(self):
        """Test risk target aggregation."""
        result = self.risk_service.aggregate_risk_targets(
            self.risk_targets, 
            {"1h": self.df}, 
            50000.0
        )
        
        self.assertIsInstance(result, AggregatedRiskTargets)
        self.assertGreater(result.stop_loss, 0)
        self.assertGreater(result.take_profit, 0)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreater(result.risk_reward_ratio, 0)
        self.assertIsInstance(result.strategy_contributions, list)
        self.assertIsInstance(result.support_resistance_analysis, dict)
    
    def test_empty_risk_targets(self):
        """Test handling of empty risk targets."""
        result = self.risk_service.aggregate_risk_targets([], None, 50000.0)
        
        self.assertIsInstance(result, AggregatedRiskTargets)
        self.assertEqual(result.stop_loss, 50000.0 * 0.98)  # 2% stop loss
        self.assertEqual(result.take_profit, 50000.0 * 1.04)  # 4% take profit
        self.assertEqual(result.confidence, 0.0)
    
    def test_risk_reward_ratio_calculation(self):
        """Test risk-reward ratio calculation."""
        # Test long position
        ratio = self.risk_service._calculate_risk_reward_ratio(49000.0, 52000.0, 50000.0)
        expected_ratio = (52000.0 - 50000.0) / (50000.0 - 49000.0)  # 2.0
        self.assertAlmostEqual(ratio, expected_ratio, places=2)
        
        # Test short position
        ratio = self.risk_service._calculate_risk_reward_ratio(51000.0, 48000.0, 50000.0)
        expected_ratio = (50000.0 - 48000.0) / (51000.0 - 50000.0)  # 2.0
        self.assertAlmostEqual(ratio, expected_ratio, places=2)
    
    def test_validate_risk_levels(self):
        """Test risk level validation."""
        # Test valid risk levels
        validation = self.risk_service.validate_risk_levels(
            49000.0, 52000.0, 50000.0, "MEDIUM"
        )
        
        self.assertIsInstance(validation, dict)
        self.assertIn("valid", validation)
        self.assertIn("risk_valid", validation)
        self.assertIn("reward_valid", validation)
        self.assertIn("ratio_valid", validation)
        self.assertIn("actual_risk", validation)
        self.assertIn("actual_reward", validation)
        self.assertIn("risk_reward_ratio", validation)
    
    def test_support_resistance_analysis(self):
        """Test support/resistance analysis."""
        analysis = self.risk_service._analyze_support_resistance(
            {"1h": self.df}, 50000.0
        )
        
        self.assertIsInstance(analysis, dict)
        self.assertIn("levels", analysis)
        self.assertIn("nearest_support", analysis)
        self.assertIn("nearest_resistance", analysis)
        self.assertIn("total_levels", analysis)
        self.assertIn("relevant_levels", analysis)
    
    def test_high_volatility_scenario(self):
        """Test risk management in high volatility scenario."""
        # Create high volatility data
        high_vol_df = self.df.copy()
        high_vol_df['high'] = high_vol_df['close'] * 1.05  # 5% higher
        high_vol_df['low'] = high_vol_df['close'] * 0.95   # 5% lower
        
        # Create risk targets for high volatility
        high_vol_targets = [
            RiskTarget(
                strategy_name="Breakout",
                stop_loss=45000.0,  # Wide stop loss
                take_profit=55000.0,  # Wide take profit
                confidence=0.6,
                strength=0.5,
                timeframe="1h"
            )
        ]
        
        result = self.risk_service.aggregate_risk_targets(
            high_vol_targets, 
            {"1h": high_vol_df}, 
            50000.0
        )
        
        # Should have wider stops in high volatility
        self.assertLess(result.stop_loss, 50000.0)
        self.assertGreater(result.take_profit, 50000.0)
    
    def test_low_volatility_scenario(self):
        """Test risk management in low volatility scenario."""
        # Create low volatility data
        low_vol_df = self.df.copy()
        low_vol_df['high'] = low_vol_df['close'] * 1.001  # 0.1% higher
        low_vol_df['low'] = low_vol_df['close'] * 0.999   # 0.1% lower
        
        # Create risk targets for low volatility
        low_vol_targets = [
            RiskTarget(
                strategy_name="Mean_Reversion",
                stop_loss=49900.0,  # Tight stop loss
                take_profit=50100.0,  # Tight take profit
                confidence=0.9,
                strength=0.9,
                timeframe="1h"
            )
        ]
        
        result = self.risk_service.aggregate_risk_targets(
            low_vol_targets, 
            {"1h": low_vol_df}, 
            50000.0
        )
        
        # Should have tighter stops in low volatility
        self.assertLess(result.stop_loss, 50000.0)
        self.assertGreater(result.take_profit, 50000.0)

    def test_entry_buffer_uses_atr_when_available(self):
        """Entry buffer should derive from ATR * profile multiplier when ATR is available."""
        svc = self.risk_service
        current_price = 100.0
        # Construct entry range around price
        entry_range = {"min": 99.0, "max": 101.0}
        # Provide ATR and profile 'balanced' (entry_buffer_atr_mult=0.7)
        atr_value = 0.2
        profile = 'balanced'
        # Start with SL/TP inside the range to force adjustment
        sl = 99.0  # for long case (< current_price)
        tp = 101.0
        adj_sl, adj_tp = svc._ensure_levels_outside_entry_range(sl, tp, entry_range, current_price, atr_value=atr_value, profile=profile)
        expected_dist = atr_value * svc._get_profile_risk_config(profile)['entry_buffer_atr_mult']
        self.assertAlmostEqual(adj_sl, entry_range['min'] - expected_dist, places=6)
        self.assertAlmostEqual(adj_tp, entry_range['max'] + expected_dist, places=6)

    def test_entry_buffer_fallback_without_atr(self):
        """When ATR is not available, buffer should fallback to 0.5% of price."""
        svc = self.risk_service
        current_price = 200.0
        entry_range = {"min": 198.0, "max": 202.0}
        sl = 198.0
        tp = 202.0
        adj_sl, adj_tp = svc._ensure_levels_outside_entry_range(sl, tp, entry_range, current_price, atr_value=None, profile='balanced')
        expected_dist = current_price * 0.005  # 0.5%
        self.assertAlmostEqual(adj_sl, entry_range['min'] - expected_dist, places=6)
        self.assertAlmostEqual(adj_tp, entry_range['max'] + expected_dist, places=6)


class TestSupportResistanceDetector(unittest.TestCase):
    """Test support/resistance level detection."""
    
    def setUp(self):
        """Set up test data."""
        self.detector = SupportResistanceDetector()
        
        # Create sample data with clear support/resistance levels
        dates = pd.date_range('2024-01-01', periods=50, freq='1H')
        
        # Create data with clear levels at 100, 200, 300
        prices = []
        for i in range(50):
            if i < 10:
                prices.append(100 + np.random.normal(0, 1))
            elif i < 20:
                prices.append(200 + np.random.normal(0, 1))
            elif i < 30:
                prices.append(300 + np.random.normal(0, 1))
            elif i < 40:
                prices.append(200 + np.random.normal(0, 1))
            else:
                prices.append(100 + np.random.normal(0, 1))
        
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p + 2 for p in prices],
            'low': [p - 2 for p in prices],
            'close': prices,
            'volume': [1000] * 50
        })
    
    def test_detect_levels(self):
        """Test level detection."""
        levels = self.detector.detect_levels(self.df)
        
        self.assertIsInstance(levels, list)
        self.assertGreater(len(levels), 0)
        
        for level in levels:
            self.assertIsInstance(level, SupportResistanceLevel)
            self.assertGreater(level.price, 0)
            self.assertGreaterEqual(level.strength, 0.0)
            self.assertLessEqual(level.strength, 1.0)
            self.assertIn(level.level_type, ['support', 'resistance'])
            self.assertGreaterEqual(level.touches, 2)
    
    def test_pivot_levels(self):
        """Test pivot point detection."""
        levels = self.detector._detect_pivot_levels(self.df)
        
        self.assertIsInstance(levels, list)
        # Should detect some levels (may not be exactly at 100, 200, 300 due to noise)
        prices = [level.price for level in levels]
        self.assertGreater(len(prices), 0)  # Should detect at least some levels
    
    def test_fractal_levels(self):
        """Test fractal level detection."""
        levels = self.detector._detect_fractal_levels(self.df)
        
        self.assertIsInstance(levels, list)
        for level in levels:
            self.assertIsInstance(level, SupportResistanceLevel)
    
    def test_volume_levels(self):
        """Test volume-based level detection."""
        levels = self.detector._detect_volume_levels(self.df)
        
        self.assertIsInstance(levels, list)
        for level in levels:
            self.assertIsInstance(level, SupportResistanceLevel)
            if level.volume_profile is not None:
                self.assertGreater(level.volume_profile, 0)
    
    def test_ma_levels(self):
        """Test moving average level detection."""
        levels = self.detector._detect_ma_levels(self.df)
        
        self.assertIsInstance(levels, list)
        for level in levels:
            self.assertIsInstance(level, SupportResistanceLevel)
    
    def test_get_relevant_levels(self):
        """Test getting relevant levels within price range."""
        levels = self.detector.detect_levels(self.df)
        relevant = self.detector.get_relevant_levels(levels, 200.0, 0.1)
        
        self.assertIsInstance(relevant, list)
        for level in relevant:
            self.assertGreaterEqual(level.price, 180.0)  # 10% below 200
            self.assertLessEqual(level.price, 220.0)     # 10% above 200
    
    def test_count_touches(self):
        """Test touch counting functionality."""
        touches = self.detector._count_touches(self.df, 200.0, 'support')
        self.assertIsInstance(touches, int)
        self.assertGreaterEqual(touches, 0)
        
        touches = self.detector._count_touches(self.df, 200.0, 'resistance')
        self.assertIsInstance(touches, int)
        self.assertGreaterEqual(touches, 0)
        
        touches = self.detector._count_touches(self.df, 200.0, 'both')
        self.assertIsInstance(touches, int)
        self.assertGreaterEqual(touches, 0)


class TestSupportResistanceLevel(unittest.TestCase):
    """Test SupportResistanceLevel dataclass."""
    
    def test_support_resistance_level_creation(self):
        """Test creating support/resistance level."""
        level = SupportResistanceLevel(
            price=100.0,
            strength=0.8,
            level_type='support',
            touches=3,
            last_touch=pd.Timestamp('2024-01-01'),
            volume_profile=1000.0
        )
        
        self.assertEqual(level.price, 100.0)
        self.assertEqual(level.strength, 0.8)
        self.assertEqual(level.level_type, 'support')
        self.assertEqual(level.touches, 3)
        self.assertIsNotNone(level.last_touch)
        self.assertEqual(level.volume_profile, 1000.0)
    
    def test_support_resistance_level_minimal(self):
        """Test creating minimal support/resistance level."""
        level = SupportResistanceLevel(
            price=200.0,
            strength=0.5,
            level_type='resistance',
            touches=2
        )
        
        self.assertEqual(level.price, 200.0)
        self.assertEqual(level.strength, 0.5)
        self.assertEqual(level.level_type, 'resistance')
        self.assertEqual(level.touches, 2)
        self.assertIsNone(level.last_touch)
        self.assertIsNone(level.volume_profile)


class TestConvenienceFunction(unittest.TestCase):
    """Test convenience function for support/resistance calculation."""
    
    def test_calculate_support_resistance_levels(self):
        """Test convenience function."""
        # Create simple test data
        dates = pd.date_range('2024-01-01', periods=20, freq='1H')
        prices = [100 + i for i in range(20)]  # Simple uptrend
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p + 1 for p in prices],
            'low': [p - 1 for p in prices],
            'close': prices,
            'volume': [1000] * 20
        })
        
        levels = calculate_support_resistance_levels(df)
        
        self.assertIsInstance(levels, list)
        for level in levels:
            self.assertIsInstance(level, SupportResistanceLevel)


class TestPositionSizing(unittest.TestCase):
    def test_position_size_by_risk(self):
        svc = RecommendationService()
        current_price = 100.0
        stop_loss = 98.0  # $2 risk per unit
        notional, pct_of_capital = svc._calculate_position_size(current_price, stop_loss, 'balanced')
        # Default capital 10k, risk 1% => $100 risk. $2 per unit => ~50 units = $5000 notional = 50% capital
        self.assertGreater(notional, 0.0)
        self.assertLessEqual(notional, 10000.0)  # Should not exceed capital
        self.assertGreater(pct_of_capital, 0.0)
        self.assertLessEqual(pct_of_capital, 1.0)


if __name__ == '__main__':
    unittest.main()
