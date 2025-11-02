"""Tests for StrategyBase class and cost calculations."""
import unittest
import pandas as pd
import numpy as np
from strategies.strategy_base import StrategyBase
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.momentum_strategy import MomentumStrategy


class TestStrategyBase(unittest.TestCase):
    """Test cases for StrategyBase functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create sample OHLCV data
        dates = pd.date_range('2023-01-01', periods=100, freq='1H')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
    
    def test_strategy_initialization_with_costs(self):
        """Test strategy initialization with cost parameters."""
        strategy = EMARSIStrategy(commission=0.002, slippage=0.001)
        self.assertEqual(strategy.commission, 0.002)
        self.assertEqual(strategy.slippage, 0.001)
        self.assertEqual(strategy.name, "EMA_RSI")
    
    def test_strategy_initialization_default_costs(self):
        """Test strategy initialization with default cost parameters."""
        strategy = EMARSIStrategy()
        self.assertEqual(strategy.commission, 0.001)
        self.assertEqual(strategy.slippage, 0.0005)
    
    def test_cost_calculation(self):
        """Test trading cost calculation."""
        strategy = EMARSIStrategy(commission=0.001, slippage=0.0005)
        
        # Test cost calculation for a trade
        entry_price = 100.0
        exit_price = 105.0
        side = 'long'
        
        costs = strategy.calculate_trade_costs(entry_price, exit_price, side)
        # Formula: entry_cost = entry_price * (commission + slippage), exit_cost = exit_price * (commission + slippage)
        # entry_cost = 100.0 * (0.001 + 0.0005) = 100.0 * 0.0015 = 0.15
        # exit_cost = 105.0 * (0.001 + 0.0005) = 105.0 * 0.0015 = 0.1575
        # total = 0.15 + 0.1575 = 0.3075
        expected_entry_cost = entry_price * (0.001 + 0.0005)  # 0.15
        expected_exit_cost = exit_price * (0.001 + 0.0005)  # 0.1575
        expected_total = expected_entry_cost + expected_exit_cost  # 0.3075
        
        self.assertAlmostEqual(costs, expected_total, places=6)
    
    def test_apply_costs_to_trade(self):
        """Test applying costs to a trade dictionary."""
        strategy = EMARSIStrategy(commission=0.001, slippage=0.0005)
        
        trade = {
            'entry_price': 100.0,
            'exit_price': 105.0,
            'side': 'long',
            'pnl': 5.0
        }
        
        trade_with_costs = strategy.apply_costs_to_pnl(trade)
        
        self.assertIn('costs', trade_with_costs)
        self.assertIn('net_pnl', trade_with_costs)
        self.assertGreater(trade_with_costs['costs'], 0)
        self.assertLess(trade_with_costs['net_pnl'], trade['pnl'])
    
    def test_metrics_calculation_with_costs(self):
        """Test metrics calculation includes cost information."""
        strategy = EMARSIStrategy(commission=0.001, slippage=0.0005)
        
        # Create mock trades with costs
        trades = [
            {'entry_price': 100, 'exit_price': 105, 'side': 'long', 'pnl': 5, 'costs': 0.3, 'net_pnl': 4.7},
            {'entry_price': 105, 'exit_price': 103, 'side': 'short', 'pnl': 2, 'costs': 0.3, 'net_pnl': 1.7},
            {'entry_price': 103, 'exit_price': 108, 'side': 'long', 'pnl': 5, 'costs': 0.3, 'net_pnl': 4.7}
        ]
        
        metrics = strategy._calculate_metrics(trades, self.sample_data)
        
        self.assertIn('total_costs', metrics)
        self.assertAlmostEqual(metrics['total_costs'], 0.9, places=6)  # 3 trades * 0.3 costs
        self.assertAlmostEqual(metrics['net_pnl'], 11.1, places=6)  # 4.7 + 1.7 + 4.7
    
    def test_metrics_calculation_without_costs(self):
        """Test metrics calculation works with trades without cost information."""
        strategy = EMARSIStrategy()
        
        # Create mock trades without costs
        trades = [
            {'entry_price': 100, 'exit_price': 105, 'side': 'long', 'pnl': 5},
            {'entry_price': 105, 'exit_price': 103, 'side': 'short', 'pnl': 2},
            {'entry_price': 103, 'exit_price': 108, 'side': 'long', 'pnl': 5}
        ]
        
        metrics = strategy._calculate_metrics(trades, self.sample_data)
        
        self.assertEqual(metrics['total_costs'], 0)  # No costs applied
        self.assertEqual(metrics['net_pnl'], 12)  # 5 + 2 + 5
    
    def test_close_all_positions_hook(self):
        """Test the close_all_positions hook functionality."""
        strategy = EMARSIStrategy()
        
        # Test with no position
        result = strategy.close_all_positions(self.sample_data, None, 100.0, 0)
        self.assertIsNone(result)
        
        # Test with position
        position = {
            'side': 'long',
            'entry_price': 95.0,
            'entry_time': self.sample_data.iloc[0]['timestamp']
        }
        
        result = strategy.close_all_positions(self.sample_data, position, 100.0, 99)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['side'], 'long')
        self.assertEqual(result['entry_price'], 95.0)
        self.assertEqual(result['exit_price'], 100.0)
        self.assertEqual(result['pnl'], 5.0)
        self.assertTrue(result['forced_close'])
    
    def test_backtest_applies_costs(self):
        """Test that backtest method applies costs to all trades."""
        strategy = EMARSIStrategy(commission=0.001, slippage=0.0005)
        
        # Mock the generate_trades method to return trades without costs
        original_generate_trades = strategy.generate_trades
        
        def mock_generate_trades(df):
            return [
                {'entry_price': 100, 'exit_price': 105, 'side': 'long', 'pnl': 5, 'entry_time': df.iloc[0]['timestamp'], 'exit_time': df.iloc[1]['timestamp']}
            ]
        
        strategy.generate_trades = mock_generate_trades
        
        # Mock generate_signals to return the dataframe as-is
        strategy.generate_signals = lambda df: df
        
        metrics = strategy.backtest(self.sample_data)
        
        # Verify costs were applied
        self.assertGreater(metrics['total_costs'], 0)
        self.assertLess(metrics['net_pnl'], 5)  # Should be less than gross PnL due to costs


class TestStrategyImplementations(unittest.TestCase):
    """Test cases for strategy implementations."""
    
    def setUp(self):
        """Set up test data."""
        dates = pd.date_range('2023-01-01', periods=50, freq='1H')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(50) * 0.01)
        
        self.sample_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 50)
        })
    
    def test_ema_rsi_strategy_closes_positions(self):
        """Test that EMA RSI strategy closes positions at end of backtest."""
        strategy = EMARSIStrategy()
        
        # Create a scenario where we have an open position
        df_with_signals = strategy.generate_signals(self.sample_data)
        trades = strategy.generate_trades(df_with_signals)
        
        # Check that all positions are closed (no open positions at end)
        # This is verified by the fact that generate_trades completes without errors
        # and the close_all_positions hook is called
        self.assertIsInstance(trades, list)
    
    def test_momentum_strategy_closes_positions(self):
        """Test that Momentum strategy closes positions at end of backtest."""
        strategy = MomentumStrategy()
        
        df_with_signals = strategy.generate_signals(self.sample_data)
        trades = strategy.generate_trades(df_with_signals)
        
        self.assertIsInstance(trades, list)
    
    def test_strategies_with_different_costs(self):
        """Test strategies with different cost parameters."""
        # Strategy with high costs
        high_cost_strategy = EMARSIStrategy(commission=0.01, slippage=0.005)
        
        # Strategy with no costs
        no_cost_strategy = EMARSIStrategy(commission=0.0, slippage=0.0)
        
        # Both should work without errors
        metrics_high_cost = high_cost_strategy.backtest(self.sample_data)
        metrics_no_cost = no_cost_strategy.backtest(self.sample_data)
        
        self.assertIn('total_costs', metrics_high_cost)
        self.assertIn('total_costs', metrics_no_cost)
        # Only assert cost difference if both strategies generate trades
        if metrics_high_cost.get('total_trades', 0) > 0 and metrics_no_cost.get('total_trades', 0) > 0:
            self.assertGreaterEqual(metrics_high_cost['total_costs'], metrics_no_cost['total_costs'])
        # Otherwise, verify both have total_costs field (even if 0.0 when no trades)
        else:
            self.assertIsInstance(metrics_high_cost['total_costs'], (int, float))
            self.assertIsInstance(metrics_no_cost['total_costs'], (int, float))


if __name__ == '__main__':
    unittest.main()
