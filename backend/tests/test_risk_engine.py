"""Unit tests for risk engine."""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.risk.engine import RiskEngine, RiskLimits, RiskMetrics
from backend.integrations.simulated_adapter import SimulatedAdapter


class TestRiskEngine(unittest.TestCase):
    """Test risk engine functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.adapter = SimulatedAdapter(initial_capital=10000.0)
        self.risk_limits = RiskLimits(
            max_exposure_pct=80.0,
            max_position_pct=25.0,
            max_drawdown_pct=20.0,
            daily_loss_limit_pct=5.0,
        )
        self.engine = RiskEngine(
            exchange_adapter=self.adapter,
            risk_limits=self.risk_limits,
        )
    
    def test_calculate_exposure(self):
        """Test exposure calculation."""
        # No positions initially
        exposure = self.engine.calculate_exposure()
        self.assertEqual(exposure['total_exposure'], 0.0)
        self.assertEqual(exposure['exposure_pct'], 0.0)
        
        # Simulate a position
        self.adapter.simulate_fill('BTCUSDT', 'buy', 0.1, 50000.0)
        exposure = self.engine.calculate_exposure()
        
        self.assertGreater(exposure['total_exposure'], 0.0)
        self.assertGreater(exposure['exposure_pct'], 0.0)
    
    def test_calculate_drawdown(self):
        """Test drawdown calculation."""
        # Initial state
        drawdown = self.engine.calculate_drawdown()
        self.assertEqual(drawdown['current_drawdown_pct'], 0.0)
        
        # Simulate equity drop
        self.adapter.peak_equity = 10000.0
        # Reduce equity to simulate loss
        self.adapter.balances['USDT']['total'] = 8000.0
        
        # Update position price to simulate loss
        account_status = self.adapter.get_account_status()
        drawdown = self.engine.calculate_drawdown()
        
        # Should show drawdown
        self.assertGreater(drawdown['current_drawdown_pct'], 0.0)
    
    def test_calculate_position_size(self):
        """Test position sizing."""
        sizing = self.engine.calculate_position_size(
            entry_price=50000.0,
            stop_loss=49000.0,
            risk_amount=100.0,  # Risk $100
        )
        
        # Position size should be calculated based on risk
        self.assertGreater(sizing['position_size'], 0.0)
        self.assertEqual(sizing['method'], 'risk_based')
        
        # Risk per unit should be $1000 (50000 - 49000)
        self.assertEqual(sizing['risk_per_unit'], 1000.0)
        # Position size should allow risking exactly $100
        expected_size = 100.0 / 1000.0  # 0.1 BTC
        self.assertAlmostEqual(sizing['position_size'], expected_size, places=6)
    
    def test_check_risk_limits(self):
        """Test risk limit checking."""
        metrics = self.engine.get_risk_metrics()
        checks = self.engine.check_risk_limits(metrics)
        
        # All checks should exist
        self.assertIn('exposure', checks)
        self.assertIn('drawdown', checks)
        self.assertIn('daily_loss', checks)
        
        # Initially, no violations
        for check_name, check_data in checks.items():
            self.assertFalse(check_data['violated'], f"{check_name} should not be violated")
    
    def test_check_risk_limits_violation(self):
        """Test risk limit violation detection."""
        # Force high exposure
        self.adapter.simulate_fill('BTCUSDT', 'buy', 10.0, 50000.0)  # $500k position
        
        metrics = self.engine.get_risk_metrics()
        checks = self.engine.check_risk_limits(metrics)
        
        # Exposure should be violated (way over 80%)
        if metrics.exposure_pct > self.risk_limits.max_exposure_pct:
            self.assertTrue(checks['exposure']['violated'])
    
    def test_position_size_limit_enforcement(self):
        """Test that position size respects maximum limits."""
        account_status = self.adapter.get_account_status()
        equity = account_status.get('equity', 10000.0)
        
        # Try to size a position that would exceed 25% limit
        sizing = self.engine.calculate_position_size(
            entry_price=50000.0,
            stop_loss=49000.0,
            risk_amount=equity * 0.5,  # Try to risk 50% (should be capped at 25%)
            method='risk_based',
        )
        
        # Position value should not exceed 25% of equity
        max_position_value = equity * 0.25
        self.assertLessEqual(sizing['position_value'], max_position_value * 1.01)  # Allow small rounding
    
    def test_var_calculation(self):
        """Test VaR calculation."""
        # Add some return history
        for i in range(100):
            self.engine.returns_history.append(0.001 * (i % 10 - 5))  # Simulated returns
        
        var_data = self.engine.calculate_var()
        
        # Should have VaR values
        self.assertIn('var_1d_95', var_data)
        self.assertIn('var_1w_95', var_data)
        
        # VaR should be positive
        self.assertGreater(var_data['var_1d_95'], 0.0)
    
    def test_daily_pnl_tracking(self):
        """Test daily P&L calculation."""
        # Start of day
        daily_pnl = self.engine.calculate_daily_pnl()
        self.assertEqual(daily_pnl, 0.0)  # No change yet
        
        # Simulate loss
        self.adapter.balances['USDT']['total'] = 9500.0
        daily_pnl = self.engine.calculate_daily_pnl()
        
        # Should show loss
        self.assertLess(daily_pnl, 0.0)


class TestRiskLimitsValidation(unittest.TestCase):
    """Test risk limit validation logic."""
    
    def test_exposure_limit(self):
        """Test exposure limit validation."""
        adapter = SimulatedAdapter(initial_capital=10000.0)
        risk_limits = RiskLimits(max_exposure_pct=50.0)  # 50% max exposure
        engine = RiskEngine(adapter, risk_limits)
        
        # Create position that exceeds limit
        adapter.simulate_fill('BTCUSDT', 'buy', 1.0, 60000.0)  # $60k position
        
        metrics = engine.get_risk_metrics()
        checks = engine.check_risk_limits(metrics)
        
        # Should violate exposure limit
        if metrics.exposure_pct > 50.0:
            self.assertTrue(checks['exposure']['violated'])


if __name__ == '__main__':
    unittest.main()

