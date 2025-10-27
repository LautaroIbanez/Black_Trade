"""Tests for BacktestEngine functionality."""
import unittest
import pandas as pd
import numpy as np
from backtest.engine import BacktestEngine
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.momentum_strategy import MomentumStrategy
from strategies.breakout_strategy import BreakoutStrategy


class TestBacktestEngine(unittest.TestCase):
    """Test cases for BacktestEngine functionality."""
    
    def setUp(self):
        """Set up test data."""
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
        
        self.engine = BacktestEngine()
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        self.assertIsInstance(self.engine, BacktestEngine)
    
    def test_single_backtest(self):
        """Test running a single backtest."""
        strategy = EMARSIStrategy()
        result = self.engine.run_backtest(strategy, self.sample_data, '1h')
        
        self.assertIsInstance(result, dict)
        self.assertIn('strategy_name', result)
        self.assertIn('timeframe', result)
        self.assertIn('total_trades', result)
        self.assertIn('net_pnl', result)
        self.assertEqual(result['strategy_name'], 'EMA_RSI')
        self.assertEqual(result['timeframe'], '1h')
    
    def test_multiple_backtests(self):
        """Test running multiple backtests."""
        strategies = [
            EMARSIStrategy(),
            MomentumStrategy(),
            BreakoutStrategy()
        ]
        
        results = self.engine.run_multiple_backtests(strategies, self.sample_data, '1h')
        
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        
        for result in results:
            self.assertIn('strategy_name', result)
            self.assertIn('timeframe', result)
            self.assertIn('total_trades', result)
            self.assertIn('net_pnl', result)
    
    def test_strategy_ranking(self):
        """Test strategy ranking functionality."""
        # Create mock results with different scores
        mock_results = [
            {'strategy_name': 'Strategy1', 'win_rate': 0.6, 'profit_factor': 1.5, 'net_pnl': 1000, 'expectancy': 50},
            {'strategy_name': 'Strategy2', 'win_rate': 0.4, 'profit_factor': 2.0, 'net_pnl': 2000, 'expectancy': 100},
            {'strategy_name': 'Strategy3', 'win_rate': 0.8, 'profit_factor': 1.2, 'net_pnl': 500, 'expectancy': 25}
        ]
        
        ranked_results = self.engine.rank_strategies(mock_results)
        
        self.assertIsInstance(ranked_results, list)
        self.assertEqual(len(ranked_results), 3)
        
        # Check that results are sorted by score (descending)
        for i in range(len(ranked_results) - 1):
            self.assertGreaterEqual(ranked_results[i].get('score', 0), ranked_results[i + 1].get('score', 0))
        
        # Check that score was added to each result
        for result in ranked_results:
            self.assertIn('score', result)
    
    def test_error_handling_in_multiple_backtests(self):
        """Test error handling when one strategy fails."""
        # Create a strategy that will fail
        class FailingStrategy:
            def __init__(self):
                self.name = "FailingStrategy"
            
            def backtest(self, df):
                raise Exception("Test error")
        
        strategies = [
            EMARSIStrategy(),
            FailingStrategy(),
            MomentumStrategy()
        ]
        
        results = self.engine.run_multiple_backtests(strategies, self.sample_data, '1h')
        
        # Should return results for successful strategies only
        self.assertEqual(len(results), 2)
        strategy_names = [r['strategy_name'] for r in results]
        self.assertIn('EMA_RSI', strategy_names)
        self.assertIn('Momentum', strategy_names)
        self.assertNotIn('FailingStrategy', strategy_names)
    
    def test_backtest_with_costs(self):
        """Test backtest with different cost configurations."""
        # Test with high costs
        high_cost_strategy = EMARSIStrategy(commission=0.01, slippage=0.005)
        high_cost_result = self.engine.run_backtest(high_cost_strategy, self.sample_data, '1h')
        
        # Test with no costs
        no_cost_strategy = EMARSIStrategy(commission=0.0, slippage=0.0)
        no_cost_result = self.engine.run_backtest(no_cost_strategy, self.sample_data, '1h')
        
        # Both should complete successfully
        self.assertIn('total_costs', high_cost_result)
        self.assertIn('total_costs', no_cost_result)
        
        # High cost strategy should have higher total costs
        if high_cost_result['total_trades'] > 0 and no_cost_result['total_trades'] > 0:
            self.assertGreater(high_cost_result['total_costs'], no_cost_result['total_costs'])
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        empty_data = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        strategy = EMARSIStrategy()
        result = self.engine.run_backtest(strategy, empty_data, '1h')
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['total_trades'], 0)
        self.assertEqual(result['net_pnl'], 0.0)


if __name__ == '__main__':
    unittest.main()
