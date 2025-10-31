"""Tests for recommendation service."""
import unittest
import pandas as pd
import numpy as np
from typing import Dict, List
from backend.services.recommendation_service import RecommendationService, StrategySignal, RecommendationResult
from strategies.ema_rsi_strategy import EMARSIStrategy
from strategies.momentum_strategy import MomentumStrategy


class TestRecommendationService(unittest.TestCase):
    """Test cases for RecommendationService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.service = RecommendationService()
        
        # Create sample OHLCV data
        dates = pd.date_range('2023-01-01', periods=100, freq='1H')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        
        self.sample_data = {
            '1h': pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': prices * 1.02,
                'low': prices * 0.98,
                'close': prices,
                'volume': np.random.randint(1000, 10000, 100)
            }),
            '4h': pd.DataFrame({
                'timestamp': dates[::4],
                'open': prices[::4],
                'high': prices[::4] * 1.02,
                'low': prices[::4] * 0.98,
                'close': prices[::4],
                'volume': np.random.randint(1000, 10000, 25)
            })
        }
        
        # Mock historical metrics
        self.historical_metrics = {
            '1h': [
                {'strategy_name': 'EMA_RSI', 'score': 0.8, 'net_pnl': 1000},
                {'strategy_name': 'Momentum', 'score': 0.6, 'net_pnl': 500}
            ],
            '4h': [
                {'strategy_name': 'EMA_RSI', 'score': 0.7, 'net_pnl': 800},
                {'strategy_name': 'Momentum', 'score': 0.9, 'net_pnl': 1200}
            ]
        }
    
    def test_service_initialization(self):
        """Test service initialization."""
        self.assertIsInstance(self.service, RecommendationService)
        self.assertIsNotNone(self.service.strategy_registry)
    
    def test_generate_recommendation_with_data(self):
        """Test generating recommendation with sample data."""
        recommendation = self.service.generate_recommendation(self.sample_data, self.historical_metrics)
        
        self.assertIsInstance(recommendation, RecommendationResult)
        self.assertIn(recommendation.action, ['BUY', 'SELL', 'HOLD'])
        self.assertGreaterEqual(recommendation.confidence, 0.0)
        self.assertLessEqual(recommendation.confidence, 1.0)
        self.assertIn(recommendation.risk_level, ['LOW', 'MEDIUM', 'HIGH'])
        self.assertIsInstance(recommendation.strategy_details, list)
    
    def test_generate_recommendation_empty_data(self):
        """Test generating recommendation with empty data."""
        empty_data = {}
        recommendation = self.service.generate_recommendation(empty_data)
        
        self.assertEqual(recommendation.action, 'HOLD')
        self.assertEqual(recommendation.confidence, 0.0)
        self.assertEqual(recommendation.risk_level, 'LOW')
        self.assertEqual(len(recommendation.strategy_details), 0)
    
    def test_strategy_signal_creation(self):
        """Test StrategySignal creation."""
        signal = StrategySignal(
            strategy_name="TestStrategy",
            signal=1,
            strength=0.8,
            confidence=0.7,
            reason="Test reason",
            price=100.0,
            timestamp="2023-01-01",
            score=0.9,
            timeframe="1h",
            entry_range={"min": 99.0, "max": 101.0},
            risk_targets={"stop_loss": 98.0, "take_profit": 102.0}
        )
        
        self.assertEqual(signal.strategy_name, "TestStrategy")
        self.assertEqual(signal.signal, 1)
        self.assertEqual(signal.strength, 0.8)
        self.assertEqual(signal.confidence, 0.7)
        self.assertEqual(signal.reason, "Test reason")
        self.assertEqual(signal.price, 100.0)
        self.assertEqual(signal.score, 0.9)
        self.assertEqual(signal.timeframe, "1h")
    
    def test_analyze_signals_buy_consensus(self):
        """Test signal analysis with buy consensus."""
        signals = [
            StrategySignal("Strategy1", 1, 0.8, 0.7, "Buy reason 1", 100.0, "2023-01-01", 0.9, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 98.0, "take_profit": 102.0}),
            StrategySignal("Strategy2", 1, 0.6, 0.6, "Buy reason 2", 100.0, "2023-01-01", 0.8, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 98.0, "take_profit": 102.0}),
            StrategySignal("Strategy3", 0, 0.0, 0.0, "Hold reason", 100.0, "2023-01-01", 0.5, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 98.0, "take_profit": 102.0})
        ]
        
        recommendation = self.service._analyze_signals(signals, data={}, profile="balanced")
        
        self.assertEqual(recommendation.action, "BUY")
        self.assertGreater(recommendation.confidence, 0.0)
        self.assertIn("Strategy1", recommendation.primary_strategy)
        self.assertGreater(len(recommendation.supporting_strategies), 0)
    
    def test_analyze_signals_sell_consensus(self):
        """Test signal analysis with sell consensus."""
        signals = [
            StrategySignal("Strategy1", -1, 0.8, 0.7, "Sell reason 1", 100.0, "2023-01-01", 0.9, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 102.0, "take_profit": 98.0}),
            StrategySignal("Strategy2", -1, 0.6, 0.6, "Sell reason 2", 100.0, "2023-01-01", 0.8, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 102.0, "take_profit": 98.0}),
            StrategySignal("Strategy3", 0, 0.0, 0.0, "Hold reason", 100.0, "2023-01-01", 0.5, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 100.0, "take_profit": 100.0})
        ]
        
        recommendation = self.service._analyze_signals(signals, data={}, profile="balanced")
        
        self.assertEqual(recommendation.action, "SELL")
        self.assertGreater(recommendation.confidence, 0.0)
        self.assertIn("Strategy1", recommendation.primary_strategy)
    
    def test_analyze_signals_hold_consensus(self):
        """Test signal analysis with hold consensus."""
        signals = [
            StrategySignal("Strategy1", 0, 0.0, 0.0, "Hold reason 1", 100.0, "2023-01-01", 0.9, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 100.0, "take_profit": 100.0}),
            StrategySignal("Strategy2", 0, 0.0, 0.0, "Hold reason 2", 100.0, "2023-01-01", 0.8, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 100.0, "take_profit": 100.0}),
            StrategySignal("Strategy3", 0, 0.0, 0.0, "Hold reason 3", 100.0, "2023-01-01", 0.5, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 100.0, "take_profit": 100.0})
        ]
        
        recommendation = self.service._analyze_signals(signals, data={}, profile="balanced")
        
        self.assertEqual(recommendation.action, "HOLD")
        self.assertEqual(recommendation.confidence, 0.0)
    
    def test_calculate_trade_levels_buy(self):
        """Static trade levels are disabled by default; ensure guard works."""
        with self.assertRaises(RuntimeError):
            self.service._calculate_trade_levels(100.0, "BUY", 0.8)
    
    def test_calculate_trade_levels_sell(self):
        """Static trade levels are disabled by default; ensure guard works."""
        with self.assertRaises(RuntimeError):
            self.service._calculate_trade_levels(100.0, "SELL", 0.8)
    
    def test_determine_risk_level(self):
        """Test risk level determination."""
        # High risk
        risk_level = self.service._determine_risk_level(0.9, 3)
        self.assertEqual(risk_level, "HIGH")
        
        # Medium risk
        risk_level = self.service._determine_risk_level(0.7, 2)
        self.assertEqual(risk_level, "MEDIUM")
        
        # Low risk
        risk_level = self.service._determine_risk_level(0.5, 1)
        self.assertEqual(risk_level, "LOW")
    
    def test_get_strategy_score(self):
        """Test getting strategy score from historical metrics."""
        score = self.service._get_strategy_score("EMA_RSI", self.historical_metrics)
        self.assertEqual(score, 0.8)  # From 1h timeframe
        
        score = self.service._get_strategy_score("Momentum", self.historical_metrics)
        self.assertEqual(score, 0.6)  # From 1h timeframe (first match)
        
        score = self.service._get_strategy_score("UnknownStrategy", self.historical_metrics)
        self.assertEqual(score, 0.5)  # Default score
    
    def test_get_strategy_consensus(self):
        """Test strategy consensus calculation."""
        signals = [
            StrategySignal("Strategy1", 1, 0.8, 0.7, "Buy 1", 100.0, "2023-01-01", 0.9, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 98.0, "take_profit": 102.0}),
            StrategySignal("Strategy2", 1, 0.6, 0.6, "Buy 2", 100.0, "2023-01-01", 0.8, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 98.0, "take_profit": 102.0}),
            StrategySignal("Strategy3", -1, 0.4, 0.4, "Sell 1", 100.0, "2023-01-01", 0.6, "1h", {"min": 99.0, "max": 101.0}, {"stop_loss": 102.0, "take_profit": 98.0})
        ]
        
        consensus = self.service.get_strategy_consensus(signals)
        
        self.assertEqual(consensus["consensus"], 1)  # Buy consensus
        self.assertAlmostEqual(consensus["agreement"], 2/3, places=2)  # 2 out of 3 agree
        self.assertAlmostEqual(consensus["buy_ratio"], 2/3, places=2)
        self.assertAlmostEqual(consensus["sell_ratio"], 1/3, places=2)
        self.assertEqual(consensus["total_strategies"], 3)
    
    def test_create_default_recommendation(self):
        """Test default recommendation creation."""
        recommendation = self.service._create_default_recommendation()
        
        self.assertEqual(recommendation.action, "HOLD")
        self.assertEqual(recommendation.confidence, 0.0)
        self.assertEqual(recommendation.risk_level, "LOW")
        self.assertEqual(len(recommendation.strategy_details), 0)
        self.assertEqual(recommendation.primary_strategy, "None")
    
    def test_signal_consistency_calculation(self):
        """Test signal consistency calculation in generate_signal."""
        strategy = EMARSIStrategy()
        
        # Create data with consistent signals
        consistent_data = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=10, freq='1H'),
            'open': [100] * 10,
            'high': [101] * 10,
            'low': [99] * 10,
            'close': [100] * 10,
            'volume': [1000] * 10
        })
        
        signal = strategy.generate_signal(consistent_data)
        
        self.assertIn("signal", signal)
        self.assertIn("strength", signal)
        self.assertIn("confidence", signal)
        self.assertIn("reason", signal)
        self.assertIn("timestamp", signal)
        self.assertIn("price", signal)
        
        # Test with empty data
        empty_signal = strategy.generate_signal(pd.DataFrame())
        self.assertEqual(empty_signal["signal"], 0)
        self.assertEqual(empty_signal["strength"], 0.0)
        self.assertEqual(empty_signal["confidence"], 0.0)


class TestStrategySignalGeneration(unittest.TestCase):
    """Test cases for strategy signal generation."""
    
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
    
    def test_ema_rsi_signal_generation(self):
        """Test EMA RSI strategy signal generation."""
        strategy = EMARSIStrategy()
        signal = strategy.generate_signal(self.sample_data)
        
        self.assertIn("signal", signal)
        self.assertIn("strength", signal)
        self.assertIn("confidence", signal)
        self.assertIn("reason", signal)
        self.assertIn("timestamp", signal)
        self.assertIn("price", signal)
        
        # Check signal value is valid
        self.assertIn(signal["signal"], [-1, 0, 1])
        
        # Check strength and confidence are in valid range
        self.assertGreaterEqual(signal["strength"], 0.0)
        self.assertLessEqual(signal["strength"], 1.0)
        self.assertGreaterEqual(signal["confidence"], 0.0)
        self.assertLessEqual(signal["confidence"], 1.0)
    
    def test_momentum_signal_generation(self):
        """Test Momentum strategy signal generation."""
        strategy = MomentumStrategy()
        signal = strategy.generate_signal(self.sample_data)
        
        self.assertIn("signal", signal)
        self.assertIn("strength", signal)
        self.assertIn("confidence", signal)
        self.assertIn("reason", signal)
        self.assertIn("timestamp", signal)
        self.assertIn("price", signal)
        
        # Check signal value is valid
        self.assertIn(signal["signal"], [-1, 0, 1])
    
    def test_signal_reason_generation(self):
        """Test signal reason generation."""
        strategy = EMARSIStrategy()
        signal = strategy.generate_signal(self.sample_data)
        
        self.assertIsInstance(signal["reason"], str)
        self.assertGreater(len(signal["reason"]), 0)
        
        # Check that reason contains relevant information
        if signal["signal"] != 0:
            self.assertIn("EMA", signal["reason"])
            self.assertIn("RSI", signal["reason"])


if __name__ == '__main__':
    unittest.main()
