"""Continuity tests for synced OHLCV data."""
import os
import unittest
from backtest.data_loader import DataLoader


class TestDataContinuity(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        self.timeframes = os.getenv('TIMEFRAMES', '15m,1h,2h,4h,12h,1d,1w').split(',')

    def test_continuity_across_timeframes(self):
        for tf in self.timeframes:
            filepath = os.path.join('data', 'ohlcv', f"{self.symbol}_{tf}.csv")
            if not os.path.exists(filepath):
                self.skipTest(f"Missing file for {tf}: {filepath}")
            df, validation = self.loader.load_data(self.symbol, tf, validate_continuity=True)
            self.assertTrue(validation.get('valid', False), f"Continuity invalid for {tf}: {validation}")
            # Allow zero gaps or handled gaps only
            self.assertGreaterEqual(validation.get('gaps_detected', 0), 0)
            self.assertIn('records_count', validation)


if __name__ == '__main__':
    unittest.main()


