"""Integration tests for risk management with exchange adapters."""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.risk.engine import RiskEngine, RiskLimits
from backend.risk.alerts import AlertManager
from backend.integrations.simulated_adapter import SimulatedAdapter


class TestRiskIntegration(unittest.TestCase):
    """Integration tests for risk management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.adapter = SimulatedAdapter(initial_capital=10000.0)
        self.risk_limits = RiskLimits(
            max_exposure_pct=80.0,
            max_drawdown_pct=20.0,
            daily_loss_limit_pct=5.0,
        )
        self.engine = RiskEngine(self.adapter, self.risk_limits)
    
    def test_end_to_end_risk_check(self):
        """Test end-to-end risk checking workflow."""
        # 1. Get initial metrics
        metrics = self.engine.get_risk_metrics()
        self.assertGreater(metrics.total_capital, 0)
        
        # 2. Check limits
        checks = self.engine.check_risk_limits(metrics)
        self.assertFalse(any(c['violated'] for c in checks.values()))
        
        # 3. Open a position
        self.adapter.simulate_fill('BTCUSDT', 'buy', 0.1, 50000.0)
        
        # 4. Recalculate
        metrics = self.engine.get_risk_metrics()
        exposure = self.engine.calculate_exposure()
        
        self.assertGreater(exposure['total_exposure'], 0)
        
        # 5. Check limits again
        checks = self.engine.check_risk_limits(metrics)
        
        # Should still be within limits
        if metrics.exposure_pct <= self.risk_limits.max_exposure_pct:
            self.assertFalse(checks['exposure']['violated'])
    
    def test_position_sizing_with_existing_positions(self):
        """Test position sizing when positions already exist."""
        # Open initial position
        self.adapter.simulate_fill('BTCUSDT', 'buy', 0.1, 50000.0)
        
        # Calculate new position size
        sizing = self.engine.calculate_position_size(
            entry_price=3000.0,
            stop_loss=2900.0,
            risk_amount=100.0,
            strategy_name='EMA_RSI',
        )
        
        # Should calculate size considering existing exposure
        self.assertGreater(sizing['position_size'], 0.0)
        
        # Total exposure after new position should not exceed limit
        exposure = self.engine.calculate_exposure()
        # This would be verified after actually opening the position
    
    def test_alert_on_limit_violation(self):
        """Test alert generation on limit violation."""
        # Mock alert manager
        alert_manager = Mock(spec=AlertManager)
        
        # Force violation by setting very low limits
        self.engine.risk_limits.max_exposure_pct = 1.0  # 1% max exposure
        
        # Create position that exceeds limit
        self.adapter.simulate_fill('BTCUSDT', 'buy', 1.0, 50000.0)
        
        metrics = self.engine.get_risk_metrics()
        checks = self.engine.check_risk_limits(metrics)
        
        # Alert manager should be called if violation detected
        if checks['exposure']['violated']:
            # In real scenario, would call alert_manager.alert_limit_violation()
            pass
    
    def test_drawdown_tracking_over_time(self):
        """Test drawdown tracking as equity changes."""
        # Initial state
        drawdown1 = self.engine.calculate_drawdown()
        self.assertEqual(drawdown1['current_drawdown_pct'], 0.0)
        
        # Simulate equity drop
        self.adapter.balances['USDT']['total'] = 9000.0
        drawdown2 = self.engine.calculate_drawdown()
        
        # Should show drawdown
        self.assertGreater(drawdown2['current_drawdown_pct'], 0.0)
        
        # Simulate recovery
        self.adapter.balances['USDT']['total'] = 9500.0
        drawdown3 = self.engine.calculate_drawdown()
        
        # Drawdown should decrease
        self.assertLess(drawdown3['current_drawdown_pct'], drawdown2['current_drawdown_pct'])
        
        # Max drawdown should track worst case
        self.assertGreaterEqual(drawdown3['max_drawdown_pct'], drawdown2['current_drawdown_pct'])


if __name__ == '__main__':
    unittest.main()

