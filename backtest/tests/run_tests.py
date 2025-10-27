"""Test runner for backtest tests."""
import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from test_strategy_base import TestStrategyBase, TestStrategyImplementations
from test_backtest_engine import TestBacktestEngine


def run_all_tests():
    """Run all backtest tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestStrategyBase))
    test_suite.addTest(unittest.makeSuite(TestStrategyImplementations))
    test_suite.addTest(unittest.makeSuite(TestBacktestEngine))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
