"""
Tests for entry range calculation in strategies.
"""

import unittest
import pandas as pd
import numpy as np
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.momentum_strategy import MomentumStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.ichimoku_strategy import IchimokuStrategy


class TestEntryRanges(unittest.TestCase):
    """Test entry range calculation for all strategies."""
    
    def setUp(self):
        """Set up test data."""
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
        
        # Create OHLCV data
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Initialize strategies
        self.ema_rsi = EMARSIStrategy()
        self.momentum = MomentumStrategy()
        self.breakout = BreakoutStrategy()
        self.mean_reversion = MeanReversionStrategy()
        self.ichimoku = IchimokuStrategy()
    
    def test_ema_rsi_entry_range(self):
        """Test EMA RSI entry range calculation."""
        # Test with buy signal
        range_buy = self.ema_rsi.entry_range(self.df, 1)
        self.assertIn('min', range_buy)
        self.assertIn('max', range_buy)
        self.assertLess(range_buy['min'], range_buy['max'])
        self.assertGreater(range_buy['min'], 0)
        self.assertGreater(range_buy['max'], 0)
        
        # Test with sell signal
        range_sell = self.ema_rsi.entry_range(self.df, -1)
        self.assertIn('min', range_sell)
        self.assertIn('max', range_sell)
        self.assertLess(range_sell['min'], range_sell['max'])
        self.assertGreater(range_sell['min'], 0)
        self.assertGreater(range_sell['max'], 0)
        
        # Test with no signal
        range_hold = self.ema_rsi.entry_range(self.df, 0)
        current_price = float(self.df['close'].iloc[-1])
        self.assertEqual(range_hold['min'], current_price)
        self.assertEqual(range_hold['max'], current_price)
    
    def test_momentum_entry_range(self):
        """Test Momentum entry range calculation."""
        # Test with buy signal
        range_buy = self.momentum.entry_range(self.df, 1)
        self.assertIn('min', range_buy)
        self.assertIn('max', range_buy)
        self.assertLess(range_buy['min'], range_buy['max'])
        self.assertGreater(range_buy['min'], 0)
        self.assertGreater(range_buy['max'], 0)
        
        # Test with sell signal
        range_sell = self.momentum.entry_range(self.df, -1)
        self.assertIn('min', range_sell)
        self.assertIn('max', range_sell)
        self.assertLess(range_sell['min'], range_sell['max'])
        self.assertGreater(range_sell['min'], 0)
        self.assertGreater(range_sell['max'], 0)
    
    def test_breakout_entry_range(self):
        """Test Breakout entry range calculation."""
        # Test with buy signal
        range_buy = self.breakout.entry_range(self.df, 1)
        self.assertIn('min', range_buy)
        self.assertIn('max', range_buy)
        self.assertLess(range_buy['min'], range_buy['max'])
        self.assertGreater(range_buy['min'], 0)
        self.assertGreater(range_buy['max'], 0)
        
        # Test with sell signal
        range_sell = self.breakout.entry_range(self.df, -1)
        self.assertIn('min', range_sell)
        self.assertIn('max', range_sell)
        self.assertLess(range_sell['min'], range_sell['max'])
        self.assertGreater(range_sell['min'], 0)
        self.assertGreater(range_sell['max'], 0)
    
    def test_mean_reversion_entry_range(self):
        """Test Mean Reversion entry range calculation."""
        # Test with buy signal
        range_buy = self.mean_reversion.entry_range(self.df, 1)
        self.assertIn('min', range_buy)
        self.assertIn('max', range_buy)
        self.assertLess(range_buy['min'], range_buy['max'])
        self.assertGreater(range_buy['min'], 0)
        self.assertGreater(range_buy['max'], 0)
        
        # Test with sell signal
        range_sell = self.mean_reversion.entry_range(self.df, -1)
        self.assertIn('min', range_sell)
        self.assertIn('max', range_sell)
        self.assertLess(range_sell['min'], range_sell['max'])
        self.assertGreater(range_sell['min'], 0)
        self.assertGreater(range_sell['max'], 0)
    
    def test_ichimoku_entry_range(self):
        """Test Ichimoku entry range calculation."""
        # Test with buy signal
        range_buy = self.ichimoku.entry_range(self.df, 1)
        self.assertIn('min', range_buy)
        self.assertIn('max', range_buy)
        self.assertLess(range_buy['min'], range_buy['max'])
        self.assertGreater(range_buy['min'], 0)
        self.assertGreater(range_buy['max'], 0)
        
        # Test with sell signal
        range_sell = self.ichimoku.entry_range(self.df, -1)
        self.assertIn('min', range_sell)
        self.assertIn('max', range_sell)
        self.assertLess(range_sell['min'], range_sell['max'])
        self.assertGreater(range_sell['min'], 0)
        self.assertGreater(range_sell['max'], 0)
    
    def test_empty_dataframe(self):
        """Test entry range with empty DataFrame."""
        empty_df = pd.DataFrame()
        
        for strategy in [self.ema_rsi, self.momentum, self.breakout, self.mean_reversion, self.ichimoku]:
            range_result = strategy.entry_range(empty_df, 1)
            self.assertEqual(range_result['min'], 0.0)
            self.assertEqual(range_result['max'], 0.0)
    
    def test_range_consistency(self):
        """Test that entry ranges are consistent across multiple calls."""
        for strategy in [self.ema_rsi, self.momentum, self.breakout, self.mean_reversion, self.ichimoku]:
            range1 = strategy.entry_range(self.df, 1)
            range2 = strategy.entry_range(self.df, 1)
            
            # Ranges should be identical for same data and signal
            self.assertAlmostEqual(range1['min'], range2['min'], places=6)
            self.assertAlmostEqual(range1['max'], range2['max'], places=6)
    
    def test_range_sensitivity_to_signal(self):
        """Test that entry ranges change based on signal type."""
        for strategy in [self.ema_rsi, self.momentum, self.breakout, self.mean_reversion, self.ichimoku]:
            range_buy = strategy.entry_range(self.df, 1)
            range_sell = strategy.entry_range(self.df, -1)
            range_hold = strategy.entry_range(self.df, 0)
            
            # Buy and sell ranges should be different (at least one component)
            ranges_different = (range_buy['min'] != range_sell['min'] or 
                              range_buy['max'] != range_sell['max'])
            self.assertTrue(ranges_different, f"Ranges should be different for {strategy.__class__.__name__}")
            
            # Hold range should be centered on current price
            current_price = float(self.df['close'].iloc[-1])
            self.assertEqual(range_hold['min'], current_price)
            self.assertEqual(range_hold['max'], current_price)


if __name__ == '__main__':
    unittest.main()
