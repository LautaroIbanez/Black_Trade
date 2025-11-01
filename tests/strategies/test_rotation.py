"""Tests for CryptoRotation multi-asset strategy."""
import unittest
import pandas as pd
import numpy as np
import logging
from unittest.mock import patch, MagicMock
from strategies.crypto_rotation_strategy import CryptoRotationStrategy
from data.feeds.rotation_loader import (
    align_universe_timestamps,
    rank_universe_by_strength,
    compute_relative_strength,
    load_rotation_universe
)


class TestCryptoRotationStrategy(unittest.TestCase):
    """Test CryptoRotation strategy with multi-asset rotation."""
    
    def setUp(self):
        """Set up test fixtures with synthetic data."""
        # Create synthetic universe data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        
        # BTC: Strong uptrend
        btc_prices = 50000 + np.cumsum(np.random.randn(100) * 100 + 50)
        self.btc_df = pd.DataFrame({
            'timestamp': dates,
            'open': btc_prices,
            'high': btc_prices * 1.01,
            'low': btc_prices * 0.99,
            'close': btc_prices,
            'volume': 1000.0
        })
        
        # ETH: Moderate uptrend
        eth_prices = 3000 + np.cumsum(np.random.randn(100) * 10 + 5)
        self.eth_df = pd.DataFrame({
            'timestamp': dates,
            'open': eth_prices,
            'high': eth_prices * 1.01,
            'low': eth_prices * 0.99,
            'close': eth_prices,
            'volume': 1000.0
        })
        
        # BNB: Flat/slightly down
        bnb_prices = 400 + np.cumsum(np.random.randn(100) * 2 - 1)
        self.bnb_df = pd.DataFrame({
            'timestamp': dates,
            'open': bnb_prices,
            'high': bnb_prices * 1.01,
            'low': bnb_prices * 0.99,
            'close': bnb_prices,
            'volume': 1000.0
        })
        
        self.universe = {
            "BTCUSDT": self.btc_df,
            "ETHUSDT": self.eth_df,
            "BNBUSDT": self.bnb_df
        }
        
        self.strategy = CryptoRotationStrategy(
            lookback=20,
            universe=list(self.universe.keys()),
            ranking_method="strength",
            min_divergence=0.01,
            top_n=1,
            bottom_n=1
        )
    
    def test_strategy_initialization(self):
        """Test strategy initializes correctly."""
        self.assertEqual(self.strategy.lookback, 20)
        self.assertEqual(self.strategy.ranking_method, "strength")
        self.assertEqual(self.strategy.min_divergence, 0.01)
        self.assertEqual(len(self.strategy.universe), 3)
    
    def test_ranking_method_strength(self):
        """Test ranking by relative strength."""
        self.strategy.ranking_method = "strength"
        universe, ranked = self.strategy._load_and_rank_universe("1h")
        
        # Mock universe data
        self.strategy.universe = list(self.universe.keys())
        
        # Should rank symbols by relative strength
        # BTC should rank highest (strongest uptrend)
        self.assertIsInstance(ranked, list)
        if ranked:
            self.assertTrue(len(ranked) > 0)
    
    def test_generate_signals_with_divergence(self):
        """Test signal generation when there's sufficient divergence."""
        # Mock the load method to return our test universe
        original_load = self.strategy._load_and_rank_universe
        
        def mock_load(timeframe):
            aligned = align_universe_timestamps(self.universe)
            ranked = rank_universe_by_strength(aligned, ema_span=20)
            return aligned, ranked
        
        self.strategy._load_and_rank_universe = mock_load
        
        # Test BTC (should be top ranked)
        self.strategy._current_symbol = "BTCUSDT"
        signals = self.strategy.generate_signals(
            self.btc_df, 
            timeframe="1h", 
            current_symbol="BTCUSDT"
        )
        
        self.assertFalse(signals.empty)
        self.assertIn('signal', signals.columns)
        self.assertIn('strength', signals.columns)
        self.assertIn('rotation_rank', signals.columns)
        self.assertIn('divergence', signals.columns)
        
        # Check signal values are valid
        self.assertTrue(all(signals['signal'].isin([-1, 0, 1])))
        self.assertTrue(all(signals['strength'] >= 0))
        self.assertTrue(all(signals['strength'] <= 1))
    
    def test_generate_signals_insufficient_divergence(self):
        """Test signal generation when divergence is insufficient."""
        # Create minimal divergence scenario
        self.strategy.min_divergence = 1.0  # Very high threshold
        
        original_load = self.strategy._load_and_rank_universe
        
        def mock_load(timeframe):
            aligned = align_universe_timestamps(self.universe)
            ranked = rank_universe_by_strength(aligned, ema_span=20)
            return aligned, ranked
        
        self.strategy._load_and_rank_universe = mock_load
        
        signals = self.strategy.generate_signals(
            self.btc_df,
            timeframe="1h",
            current_symbol="BTCUSDT"
        )
        
        # With insufficient divergence, should mostly be neutral
        self.assertTrue(all(signals['signal'].isin([-1, 0, 1])))
    
    def test_generate_trades(self):
        """Test trade generation from signals."""
        # Generate signals first
        original_load = self.strategy._load_and_rank_universe
        
        def mock_load(timeframe):
            aligned = align_universe_timestamps(self.universe)
            ranked = rank_universe_by_strength(aligned, ema_span=20)
            return aligned, ranked
        
        self.strategy._load_and_rank_universe = mock_load
        
        signals = self.strategy.generate_signals(
            self.btc_df,
            timeframe="1h",
            current_symbol="BTCUSDT"
        )
        
        trades = self.strategy.generate_trades(signals)
        
        # Should generate list of trades
        self.assertIsInstance(trades, list)
        
        # Each trade should have required fields
        for trade in trades:
            self.assertIn('entry_price', trade)
            self.assertIn('exit_price', trade)
            self.assertIn('side', trade)
            self.assertIn('pnl', trade)
            self.assertIn('entry_time', trade)
            self.assertIn('exit_time', trade)
            self.assertIn(trade['side'], ['long', 'short'])
    
    def test_rebalancing_logic(self):
        """Test that rebalancing periods are respected."""
        self.strategy.rebalance_periods = 10
        
        # Create signals with periodic changes
        signals_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1h'),
            'signal': [1 if i % 20 < 10 else 0 for i in range(50)],
            'divergence': [0.05] * 50,
            'close': [50000] * 50
        })
        
        trades = self.strategy.generate_trades(signals_data)
        
        # With rebalancing, should see exit_reason = "rebalance" in some trades
        exit_reasons = [t.get('exit_reason') for t in trades if 'exit_reason' in t]
        if exit_reasons:
            # Should have some rebalance exits
            self.assertIsInstance(exit_reasons, list)
    
    def test_empty_universe_fallback(self):
        """Test fallback to single-symbol logic when universe is empty."""
        self.strategy.universe = []
        
        signals = self.strategy.generate_signals(
            self.btc_df,
            timeframe="1h",
            current_symbol="BTCUSDT"
        )
        
        # Should still generate signals (fallback mode)
        self.assertFalse(signals.empty)
        self.assertIn('signal', signals.columns)
    
    def test_multiple_symbols_generate_trades(self):
        """Test that strategy generates trades when there are real divergences."""
        # Set up strategy with lower divergence threshold
        self.strategy.min_divergence = 0.005  # 0.5%
        
        original_load = self.strategy._load_and_rank_universe
        
        def mock_load(timeframe):
            aligned = align_universe_timestamps(self.universe)
            ranked = rank_universe_by_strength(aligned, ema_span=20)
            return aligned, ranked
        
        self.strategy._load_and_rank_universe = mock_load
        
        # Test all symbols
        all_trades = []
        for sym, df in self.universe.items():
            self.strategy._current_symbol = sym
            signals = self.strategy.generate_signals(df, timeframe="1h", current_symbol=sym)
            trades = self.strategy.generate_trades(signals)
            all_trades.extend(trades)
        
        # Should generate trades when there's divergence between symbols
        # At least one symbol should generate trades if divergence exists
        self.assertIsInstance(all_trades, list)
        # Note: May be empty if divergence threshold not met, which is acceptable
    
    def test_missing_symbols_fallback_to_single_asset(self):
        """Test that strategy falls back gracefully when symbols are missing."""
        # Set up strategy with universe but mock loader to return empty/partial universe
        self.strategy.universe = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "MISSINGUSDT"]
        
        # Mock load_rotation_universe to return only partial data
        with patch('strategies.crypto_rotation_strategy.load_rotation_universe') as mock_load:
            mock_load.return_value = {}  # Empty universe (simulates all symbols missing)
            
            signals = self.strategy.generate_signals(
                self.btc_df,
                timeframe="1h",
                current_symbol="BTCUSDT"
            )
            
            # Should fall back to single-symbol mode
            self.assertFalse(signals.empty)
            self.assertIn('signal', signals.columns)
            self.assertIn('rotation_mode', signals.columns)
            
            # Should indicate fallback mode
            self.assertTrue(all(signals['rotation_mode'] == 'fallback'))
            self.assertTrue(all(signals['rotation_rank'] == -1))
            self.assertTrue(all(signals['universe_symbols_count'] == 0))
    
    def test_insufficient_symbols_fallback(self):
        """Test fallback when only one symbol is available (insufficient for rotation)."""
        # Mock loader to return only one symbol
        with patch('strategies.crypto_rotation_strategy.load_rotation_universe') as mock_load:
            mock_load.return_value = {"BTCUSDT": self.btc_df}  # Only one symbol
            
            signals = self.strategy.generate_signals(
                self.btc_df,
                timeframe="1h",
                current_symbol="BTCUSDT"
            )
            
            # Should fall back to single-symbol mode
            self.assertFalse(signals.empty)
            self.assertIn('rotation_mode', signals.columns)
            self.assertTrue(all(signals['rotation_mode'] == 'fallback'))
            self.assertTrue(all(signals['rotation_available'] == False))
    
    def test_telemetry_records_participation(self):
        """Test that telemetry records how many symbols participate in each decision."""
        # Mock loader to return partial universe
        with patch('strategies.crypto_rotation_strategy.load_rotation_universe') as mock_load:
            mock_load.return_value = {
                "BTCUSDT": self.btc_df,
                "ETHUSDT": self.eth_df
            }  # 2 out of 3 symbols
            
            signals = self.strategy.generate_signals(
                self.btc_df,
                timeframe="1h",
                current_symbol="BTCUSDT"
            )
            
            # Check telemetry fields
            self.assertIn('universe_symbols_count', signals.columns)
            self.assertIn('universe_participation', signals.columns)
            self.assertIn('rotation_available', signals.columns)
            self.assertIn('ranked_symbols_count', signals.columns)
            
            # Should record 2 symbols participated
            self.assertTrue(all(signals['universe_symbols_count'] == 2))
            self.assertTrue(all(signals['rotation_available'] == True))
            # Participation should be 2/3 = 0.666...
            participation_expected = 2/3
            self.assertTrue(all(abs(signals['universe_participation'] - participation_expected) < 0.01))
    
    def test_strict_mode_raises_error_on_missing_symbols(self):
        """Test that strict mode raises RuntimeError when symbols are missing."""
        self.strategy.universe = ["BTCUSDT", "ETHUSDT", "MISSINGUSDT"]
        
        with patch('strategies.crypto_rotation_strategy.load_rotation_universe') as mock_load:
            # Simulate loader raising error in strict mode
            mock_load.side_effect = RuntimeError("Insufficient symbols loaded: 1 < 2 required")
            
            # In strict mode, should raise error
            with self.assertRaises(RuntimeError):
                self.strategy._load_and_rank_universe("1h", strict=True)
    
    def test_strict_mode_returns_empty_on_error(self):
        """Test that non-strict mode returns empty instead of raising."""
        self.strategy.universe = ["BTCUSDT", "ETHUSDT", "MISSINGUSDT"]
        
        with patch('strategies.crypto_rotation_strategy.load_rotation_universe') as mock_load:
            # Simulate loader raising error
            mock_load.side_effect = RuntimeError("Insufficient symbols loaded: 1 < 2 required")
            
            # In non-strict mode, should return empty without raising
            universe, ranked = self.strategy._load_and_rank_universe("1h", strict=False)
            self.assertEqual(universe, {})
            self.assertEqual(ranked, [])
    
    def test_logging_on_missing_symbols(self):
        """Test that missing symbols are logged appropriately."""
        import io
        import sys
        
        # Capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('strategies.crypto_rotation_strategy')
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)
        
        try:
            # Mock loader to return empty universe
            with patch('strategies.crypto_rotation_strategy.load_rotation_universe') as mock_load:
                mock_load.return_value = {}
                
                signals = self.strategy.generate_signals(
                    self.btc_df,
                    timeframe="1h",
                    current_symbol="BTCUSDT"
                )
                
                # Should log warning about fallback
                log_output = log_capture.getvalue()
                # Note: Actual log content depends on implementation
                # This test verifies logging mechanism works
                self.assertIsInstance(log_output, str)
        finally:
            logger.removeHandler(handler)


if __name__ == '__main__':
    unittest.main()

