"""
Data loader with temporal continuity validation and missing data handling.

This module provides robust data loading with validation and gap detection.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DataLoader:
    """Data loader with temporal continuity validation."""
    
    def __init__(self, data_dir: str = "data/ohlcv"):
        """Initialize data loader."""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Timeframe intervals in minutes
        self.interval_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
        }
        
        logger.info(f"DataLoader initialized with data_dir: {data_dir}")
    
    def load_data(self, symbol: str, timeframe: str, 
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  validate_continuity: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Load OHLCV data with temporal continuity validation.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h', '4h', '1d')
            start_date: Start date for data filtering
            end_date: End date for data filtering
            validate_continuity: Whether to validate temporal continuity
            
        Returns:
            Tuple of (dataframe, validation_report)
        """
        try:
            # Load raw data
            df = self._load_raw_data(symbol, timeframe)
            
            if df.empty:
                return df, {"error": "No data available", "valid": False}
            
            # Convert timestamp to datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('datetime').reset_index(drop=True)
            
            # Filter by date range if specified
            if start_date:
                df = df[df['datetime'] >= start_date]
            if end_date:
                df = df[df['datetime'] <= end_date]
            
            # Validate temporal continuity
            validation_report = {}
            if validate_continuity:
                validation_report = self._validate_temporal_continuity(df, timeframe)
            
            # Handle missing data
            if validation_report.get('gaps_detected', 0) > 0:
                df = self._handle_missing_data(df, timeframe, validation_report)
            
            # Final validation
            final_validation = self._final_validation(df, timeframe)
            validation_report.update(final_validation)
            
            logger.info(f"Loaded {len(df)} candles for {symbol} {timeframe}")
            return df, validation_report
            
        except (FileNotFoundError, ValueError) as e:
            # Re-raise these specific exceptions for testing
            raise
        except Exception as e:
            logger.error(f"Error loading data for {symbol} {timeframe}: {e}")
            return pd.DataFrame(), {"error": str(e), "valid": False}
    
    def load_multiple_timeframes(self, symbol: str, timeframes: List[str],
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None) -> Dict[str, Tuple[pd.DataFrame, Dict[str, Any]]]:
        """Load data for multiple timeframes."""
        results = {}
        
        for timeframe in timeframes:
            try:
                df, validation = self.load_data(
                    symbol, timeframe, start_date, end_date
                )
                results[timeframe] = (df, validation)
            except Exception as e:
                logger.error(f"Error loading {timeframe}: {e}")
                results[timeframe] = (pd.DataFrame(), {"error": str(e), "valid": False})
        
        return results
    
    def _load_raw_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load raw data from CSV file."""
        filepath = self.data_dir / f"{symbol}_{timeframe}.csv"
        
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {e}")
        
        # Validate required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        return df
    
    def _validate_temporal_continuity(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Validate temporal continuity of the data."""
        if df.empty:
            return {"valid": False, "error": "Empty dataframe"}
        
        interval_minutes = self.interval_minutes.get(timeframe, 60)
        expected_interval = pd.Timedelta(minutes=interval_minutes)
        
        # Calculate actual intervals
        df['interval'] = df['datetime'].diff()
        
        # Find gaps (intervals larger than expected)
        tolerance = expected_interval * 0.1  # 10% tolerance
        gaps = df[df['interval'] > expected_interval + tolerance]
        
        # Calculate metrics
        total_candles = len(df)
        gaps_detected = len(gaps)
        gap_percentage = (gaps_detected / total_candles) * 100 if total_candles > 0 else 0
        
        # Check for duplicate timestamps
        duplicates = df[df['datetime'].duplicated()]
        duplicate_count = len(duplicates)
        
        # Check data freshness
        latest_candle = df['datetime'].iloc[-1]
        current_time = datetime.now()
        freshness_hours = (current_time - latest_candle).total_seconds() / 3600
        
        # Calculate completeness
        date_range = (df['datetime'].max() - df['datetime'].min()).total_seconds() / 3600
        expected_candles = int(date_range * 60 / interval_minutes)
        completeness = (total_candles / expected_candles) * 100 if expected_candles > 0 else 0
        
        validation_report = {
            "valid": gaps_detected == 0 and duplicate_count == 0,
            "total_candles": total_candles,
            "gaps_detected": gaps_detected,
            "gap_percentage": gap_percentage,
            "duplicate_timestamps": duplicate_count,
            "freshness_hours": freshness_hours,
            "is_fresh": freshness_hours < 2,
            "completeness_percentage": min(completeness, 100),
            "date_range_hours": date_range,
            "expected_interval_minutes": interval_minutes,
            "gaps": gaps[['datetime', 'interval']].to_dict('records') if not gaps.empty else []
        }
        
        return validation_report
    
    def _handle_missing_data(self, df: pd.DataFrame, timeframe: str, 
                           validation_report: Dict[str, Any]) -> pd.DataFrame:
        """Handle missing data by interpolation or forward fill."""
        if df.empty:
            return df
        
        interval_minutes = self.interval_minutes.get(timeframe, 60)
        expected_interval = pd.Timedelta(minutes=interval_minutes)
        
        # Create complete time series
        start_time = df['datetime'].min()
        end_time = df['datetime'].max()
        
        # Generate expected timestamps
        expected_timestamps = pd.date_range(
            start=start_time,
            end=end_time,
            freq=f"{interval_minutes}T"
        )
        
        # Create complete dataframe
        complete_df = pd.DataFrame({
            'datetime': expected_timestamps,
            'timestamp': expected_timestamps.astype(np.int64) // 10**6
        })
        
        # Merge with existing data
        merged_df = complete_df.merge(df, on='datetime', how='left')
        
        # Clean up duplicate timestamp columns
        if 'timestamp_x' in merged_df.columns and 'timestamp_y' in merged_df.columns:
            merged_df['timestamp'] = merged_df['timestamp_y'].fillna(merged_df['timestamp_x'])
            merged_df = merged_df.drop(['timestamp_x', 'timestamp_y'], axis=1)
        elif 'timestamp_x' in merged_df.columns:
            merged_df['timestamp'] = merged_df['timestamp_x']
            merged_df = merged_df.drop('timestamp_x', axis=1)
        
        # Forward fill missing values
        merged_df = merged_df.ffill()
        
        # If still missing values at the beginning, backfill
        merged_df = merged_df.bfill()
        
        # Remove any remaining NaN values
        merged_df = merged_df.dropna()
        
        logger.info(f"Handled missing data: {len(df)} -> {len(merged_df)} candles")
        
        return merged_df
    
    def _get_interval_minutes(self, timeframe: str) -> int:
        """Get interval in minutes for a timeframe."""
        return self.interval_minutes.get(timeframe, 60)
    
    def _final_validation(self, df: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Perform final validation on the processed data."""
        if df.empty:
            return {"final_valid": False, "error": "Empty dataframe"}
        
        # Check for required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {"final_valid": False, "error": f"Missing columns: {missing_columns}"}
        
        # Check for negative prices
        price_columns = ['open', 'high', 'low', 'close']
        negative_prices = df[price_columns].lt(0).any().any()
        
        if negative_prices:
            return {"final_valid": False, "error": "Negative prices detected"}
        
        # Check for zero volume
        zero_volume = (df['volume'] == 0).sum()
        zero_volume_percentage = (zero_volume / len(df)) * 100
        
        # Check OHLC consistency
        ohlc_errors = 0
        for _, row in df.iterrows():
            if not (row['low'] <= row['open'] <= row['high'] and 
                   row['low'] <= row['close'] <= row['high']):
                ohlc_errors += 1
        
        ohlc_error_percentage = (ohlc_errors / len(df)) * 100
        
        # Calculate data quality score
        quality_score = 100
        quality_score -= zero_volume_percentage * 0.5  # Penalize zero volume
        quality_score -= ohlc_error_percentage * 2  # Penalize OHLC errors
        quality_score = max(0, quality_score)
        
        return {
            "final_valid": True,
            "total_candles": len(df),
            "zero_volume_count": zero_volume,
            "zero_volume_percentage": zero_volume_percentage,
            "ohlc_errors": ohlc_errors,
            "ohlc_error_percentage": ohlc_error_percentage,
            "quality_score": quality_score,
            "data_quality": "excellent" if quality_score >= 95 else 
                           "good" if quality_score >= 85 else
                           "fair" if quality_score >= 70 else
                           "poor"
        }
    
    def get_data_summary(self, symbol: str, timeframes: List[str]) -> Dict[str, Any]:
        """Get summary of data availability and quality for multiple timeframes."""
        summary = {
            "symbol": symbol,
            "timeframes": {},
            "overall_status": "unknown",
            "timestamp": datetime.now().isoformat()
        }
        
        valid_timeframes = 0
        total_timeframes = len(timeframes)
        
        for timeframe in timeframes:
            try:
                df, validation = self.load_data(symbol, timeframe, validate_continuity=True)
                
                timeframe_summary = {
                    "available": not df.empty,
                    "candles": len(df),
                    "valid": validation.get("valid", False),
                    "fresh": validation.get("is_fresh", False),
                    "completeness": validation.get("completeness_percentage", 0),
                    "gaps": validation.get("gaps_detected", 0),
                    "quality": validation.get("data_quality", "unknown")
                }
                
                if timeframe_summary["available"] and timeframe_summary["valid"]:
                    valid_timeframes += 1
                
                summary["timeframes"][timeframe] = timeframe_summary
                
            except Exception as e:
                summary["timeframes"][timeframe] = {
                    "available": False,
                    "error": str(e)
                }
        
        # Determine overall status
        if valid_timeframes == total_timeframes:
            summary["overall_status"] = "excellent"
        elif valid_timeframes >= total_timeframes * 0.8:
            summary["overall_status"] = "good"
        elif valid_timeframes >= total_timeframes * 0.5:
            summary["overall_status"] = "fair"
        else:
            summary["overall_status"] = "poor"
        
        return summary


# Global instance
data_loader = DataLoader()
