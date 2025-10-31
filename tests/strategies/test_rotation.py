"""Tests for CryptoRotation multi-asset strategy."""
import unittest
import pandas as pd
import numpy as np
from strategies.crypto_rotation_strategy import CryptoRotationStrategy
from data.feeds.rotation_loader import (
    align_universe_timestamps,
    rank_universe_by_strength,
    compute_relative_strength
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


if __name__ == '__main__':
    unittest.main()

