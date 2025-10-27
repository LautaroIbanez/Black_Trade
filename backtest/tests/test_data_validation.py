"""
Tests for data validation and quality checks.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from backtest.data_loader import DataLoader


class TestDataLoader(unittest.TestCase):
    """Test data loader functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.data_loader = DataLoader(data_dir=self.temp_dir)
        
        # Create sample OHLCV data
        self.sample_data = self._create_sample_data()
        
        # Save sample data to file
        self.symbol = "TESTUSDT"
        self.timeframe = "1h"
        self._save_sample_data()
    
    def tearDown(self):
        """Clean up test data."""
        shutil.rmtree(self.temp_dir)
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample OHLCV data with known gaps."""
        # Create 100 hours of data with some gaps
        start_time = datetime.now() - timedelta(days=5)
        timestamps = []
        
        for i in range(100):
            if i not in [20, 21, 45, 46, 47]:  # Create gaps
                timestamps.append(start_time + timedelta(hours=i))
        
        data = []
        base_price = 50000
        
        for i, timestamp in enumerate(timestamps):
            price_change = np.random.normal(0, 100)
            open_price = base_price + price_change
            high_price = open_price + abs(np.random.normal(0, 50))
            low_price = open_price - abs(np.random.normal(0, 50))
            close_price = open_price + np.random.normal(0, 30)
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': int(timestamp.timestamp() * 1000),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })
            
            base_price = close_price
        
        return pd.DataFrame(data)
    
    def _save_sample_data(self):
        """Save sample data to CSV file."""
        filepath = Path(self.temp_dir) / f"{self.symbol}_{self.timeframe}.csv"
        self.sample_data.to_csv(filepath, index=False)
    
    def test_load_data_basic(self):
        """Test basic data loading."""
        df, validation = self.data_loader.load_data(
            self.symbol, self.timeframe, validate_continuity=True
        )
        
        self.assertFalse(df.empty)
        self.assertIn('datetime', df.columns)
        self.assertIn('timestamp', df.columns)
        self.assertIn('open', df.columns)
        self.assertIn('high', df.columns)
        self.assertIn('low', df.columns)
        self.assertIn('close', df.columns)
        self.assertIn('volume', df.columns)
    
    def test_temporal_continuity_validation(self):
        """Test temporal continuity validation."""
        df, validation = self.data_loader.load_data(
            self.symbol, self.timeframe, validate_continuity=True
        )
        
        self.assertIn('valid', validation)
        self.assertIn('gaps_detected', validation)
        self.assertIn('gap_percentage', validation)
        self.assertIn('duplicate_timestamps', validation)
        self.assertIn('freshness_hours', validation)
        self.assertIn('completeness_percentage', validation)
        
        # Should detect gaps in our sample data
        self.assertGreater(validation['gaps_detected'], 0)
        self.assertFalse(validation['valid'])  # Should be invalid due to gaps
    
    def test_missing_data_handling(self):
        """Test handling of missing data."""
        df, validation = self.data_loader.load_data(
            self.symbol, self.timeframe, validate_continuity=True
        )
        
        # Should handle gaps by interpolation
        self.assertGreater(len(df), len(self.sample_data))
        self.assertFalse(df['open'].isna().any())
        self.assertFalse(df['high'].isna().any())
        self.assertFalse(df['low'].isna().any())
        self.assertFalse(df['close'].isna().any())
        self.assertFalse(df['volume'].isna().any())
    
    def test_final_validation(self):
        """Test final validation checks."""
        df, validation = self.data_loader.load_data(
            self.symbol, self.timeframe, validate_continuity=True
        )
        
        self.assertIn('final_valid', validation)
        self.assertIn('total_candles', validation)
        self.assertIn('zero_volume_count', validation)
        self.assertIn('ohlc_errors', validation)
        self.assertIn('quality_score', validation)
        self.assertIn('data_quality', validation)
        
        # Should be valid after gap filling
        self.assertTrue(validation['final_valid'])
        self.assertGreater(validation['quality_score'], 0)
    
    def test_load_multiple_timeframes(self):
        """Test loading multiple timeframes."""
        # Create additional timeframe data
        timeframes = ['1h', '4h']
        results = {}
        
        for tf in timeframes:
            filepath = Path(self.temp_dir) / f"{self.symbol}_{tf}.csv"
            self.sample_data.to_csv(filepath, index=False)
        
        results = self.data_loader.load_multiple_timeframes(
            self.symbol, timeframes
        )
        
        self.assertEqual(len(results), 2)
        self.assertIn('1h', results)
        self.assertIn('4h', results)
        
        for tf in timeframes:
            df, validation = results[tf]
            self.assertFalse(df.empty)
            self.assertIn('valid', validation)
    
    def test_data_summary(self):
        """Test data summary generation."""
        summary = self.data_loader.get_data_summary(
            self.symbol, [self.timeframe]
        )
        
        self.assertIn('symbol', summary)
        self.assertIn('timeframes', summary)
        self.assertIn('overall_status', summary)
        self.assertIn('timestamp', summary)
        
        self.assertEqual(summary['symbol'], self.symbol)
        self.assertIn(self.timeframe, summary['timeframes'])
        
        timeframe_info = summary['timeframes'][self.timeframe]
        self.assertIn('available', timeframe_info)
        self.assertIn('candles', timeframe_info)
        self.assertIn('valid', timeframe_info)
        self.assertIn('fresh', timeframe_info)
        self.assertIn('completeness', timeframe_info)
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        # Create empty file
        empty_file = Path(self.temp_dir) / f"{self.symbol}_empty.csv"
        empty_file.write_text("timestamp,open,high,low,close,volume\n")
        
        df, validation = self.data_loader.load_data(
            self.symbol, "empty", validate_continuity=True
        )
        
        self.assertTrue(df.empty)
        self.assertFalse(validation.get('valid', True))
        self.assertIn('error', validation)
    
    def test_invalid_data_handling(self):
        """Test handling of invalid data."""
        # Create file with missing columns
        invalid_file = Path(self.temp_dir) / f"{self.symbol}_invalid.csv"
        invalid_data = pd.DataFrame({
            'timestamp': [int(datetime.now().timestamp() * 1000)],
            'price': [50000]  # Missing required columns
        })
        invalid_data.to_csv(invalid_file, index=False)
        
        with self.assertRaises(ValueError):
            self.data_loader.load_data(
                self.symbol, "invalid", validate_continuity=True
            )
    
    def test_negative_prices_detection(self):
        """Test detection of negative prices."""
        # Create data with negative prices
        invalid_data = pd.DataFrame({
            'timestamp': [int(datetime.now().timestamp() * 1000)],
            'open': [-1000],  # Negative price
            'high': [50000],
            'low': [49000],
            'close': [49500],
            'volume': [1000]
        })
        
        invalid_file = Path(self.temp_dir) / f"{self.symbol}_negative.csv"
        invalid_data.to_csv(invalid_file, index=False)
        
        df, validation = self.data_loader.load_data(
            self.symbol, "negative", validate_continuity=True
        )
        
        self.assertFalse(validation.get('final_valid', True))
        self.assertIn('error', validation)
    
    def test_ohlc_consistency_validation(self):
        """Test OHLC consistency validation."""
        # Create data with OHLC inconsistencies
        inconsistent_data = pd.DataFrame({
            'timestamp': [int(datetime.now().timestamp() * 1000)],
            'open': [50000],
            'high': [49000],  # High < Open (invalid)
            'low': [51000],   # Low > Open (invalid)
            'close': [49500],
            'volume': [1000]
        })
        
        inconsistent_file = Path(self.temp_dir) / f"{self.symbol}_inconsistent.csv"
        inconsistent_data.to_csv(inconsistent_file, index=False)
        
        df, validation = self.data_loader.load_data(
            self.symbol, "inconsistent", validate_continuity=True
        )
        
        self.assertIn('ohlc_errors', validation)
        self.assertGreater(validation['ohlc_errors'], 0)
        self.assertIn('ohlc_error_percentage', validation)
    
    def test_date_filtering(self):
        """Test date range filtering."""
        start_date = datetime.now() - timedelta(days=2)
        end_date = datetime.now() - timedelta(days=1)
        
        df, validation = self.data_loader.load_data(
            self.symbol, self.timeframe,
            start_date=start_date,
            end_date=end_date,
            validate_continuity=True
        )
        
        if not df.empty:
            self.assertTrue((df['datetime'] >= start_date).all())
            self.assertTrue((df['datetime'] <= end_date).all())
    
    def test_interval_minutes_mapping(self):
        """Test interval minutes mapping."""
        # Test various timeframes
        test_cases = [
            ('1m', 1), ('5m', 5), ('15m', 15), ('30m', 30),
            ('1h', 60), ('4h', 240), ('1d', 1440), ('1w', 10080)
        ]
        
        for timeframe, expected_minutes in test_cases:
            actual_minutes = self.data_loader._get_interval_minutes(timeframe)
            self.assertEqual(actual_minutes, expected_minutes)
    
    def test_quality_score_calculation(self):
        """Test data quality score calculation."""
        # Create perfect data
        perfect_data = pd.DataFrame({
            'timestamp': [int(datetime.now().timestamp() * 1000)],
            'open': [50000],
            'high': [51000],
            'low': [49000],
            'close': [50500],
            'volume': [1000]
        })
        
        perfect_file = Path(self.temp_dir) / f"{self.symbol}_perfect.csv"
        perfect_data.to_csv(perfect_file, index=False)
        
        df, validation = self.data_loader.load_data(
            self.symbol, "perfect", validate_continuity=True
        )
        
        self.assertIn('quality_score', validation)
        self.assertGreaterEqual(validation['quality_score'], 0)
        self.assertLessEqual(validation['quality_score'], 100)
        
        # Perfect data should have high quality score
        if validation['final_valid']:
            self.assertGreaterEqual(validation['quality_score'], 90)


class TestDataValidationEdgeCases(unittest.TestCase):
    """Test edge cases for data validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_loader = DataLoader(data_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            self.data_loader.load_data("NONEXISTENT", "1h")
    
    def test_corrupted_csv(self):
        """Test handling of corrupted CSV file."""
        corrupted_file = Path(self.temp_dir) / "CORRUPTED_1h.csv"
        corrupted_file.write_text("invalid,csv,content\nwith,missing,columns")
        
        with self.assertRaises((ValueError, pd.errors.EmptyDataError)):
            self.data_loader.load_data("CORRUPTED", "1h")
    
    def test_very_large_gaps(self):
        """Test handling of very large gaps in data."""
        # Create data with very large gap
        timestamps = [
            int((datetime.now() - timedelta(days=10)).timestamp() * 1000),
            int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        ]
        
        large_gap_data = pd.DataFrame({
            'timestamp': timestamps,
            'open': [50000, 51000],
            'high': [51000, 52000],
            'low': [49000, 50000],
            'close': [50500, 51500],
            'volume': [1000, 1000]
        })
        
        large_gap_file = Path(self.temp_dir) / "LARGEGAP_1h.csv"
        large_gap_data.to_csv(large_gap_file, index=False)
        
        df, validation = self.data_loader.load_data(
            "LARGEGAP", "1h", validate_continuity=True
        )
        
        self.assertIn('gaps_detected', validation)
        self.assertGreater(validation['gaps_detected'], 0)
        self.assertIn('gap_percentage', validation)
    
    def test_zero_volume_handling(self):
        """Test handling of zero volume data."""
        zero_volume_data = pd.DataFrame({
            'timestamp': [int(datetime.now().timestamp() * 1000)],
            'open': [50000],
            'high': [51000],
            'low': [49000],
            'close': [50500],
            'volume': [0]  # Zero volume
        })
        
        zero_volume_file = Path(self.temp_dir) / "ZEROVOL_1h.csv"
        zero_volume_data.to_csv(zero_volume_file, index=False)
        
        df, validation = self.data_loader.load_data(
            "ZEROVOL", "1h", validate_continuity=True
        )
        
        self.assertIn('zero_volume_count', validation)
        self.assertGreater(validation['zero_volume_count'], 0)
        self.assertIn('zero_volume_percentage', validation)


if __name__ == '__main__':
    unittest.main()
