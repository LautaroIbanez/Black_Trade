"""
Scheduled sync job for data synchronization and validation.

This job runs periodically to ensure data freshness and completeness.
"""

import os
import sys
import logging
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from data.binance_client import BinanceClient
from data.sync_service import SyncService
from backend.services.strategy_registry import strategy_registry

# Configure logging
log_dir = Path(project_root) / "backend" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "data_sync.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SyncJob:
    """Scheduled job for data synchronization and validation."""
    
    def __init__(self):
        """Initialize sync job."""
        self.binance_client = BinanceClient()
        self.sync_service = SyncService(self.binance_client)
        self.symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        self.timeframes = os.getenv('TIMEFRAMES', '15m,1h,2h,4h,12h,1d,1w').split(',')
        
        logger.info(f"SyncJob initialized for {self.symbol} on {self.timeframes}")
    
    def run_full_sync(self) -> Dict[str, Any]:
        """Run full data synchronization."""
        logger.info("Starting full data synchronization")
        start_time = datetime.now()
        
        try:
            # Download historical data with pagination
            results = self.sync_service.download_historical_data(
                symbol=self.symbol,
                timeframes=self.timeframes,
                days_back=365
            )
            
            # Detect and fill gaps
            gap_results = self.sync_service.detect_and_fill_gaps(
                symbol=self.symbol,
                timeframes=self.timeframes
            )
            
            # Validate current day data
            validation_results = {}
            for timeframe in self.timeframes:
                validation_results[timeframe] = self.sync_service.validate_current_day_data(
                    self.symbol, timeframe
                )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Prepare results
            sync_results = {
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "symbol": self.symbol,
                "timeframes": self.timeframes,
                "download_results": results,
                "gap_results": gap_results,
                "validation_results": validation_results,
                "status": "success"
            }
            
            # Log results
            self._log_sync_results(sync_results)
            
            logger.info(f"Full sync completed in {duration:.2f} seconds")
            return sync_results
            
        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            return {
                "timestamp": start_time.isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def run_incremental_sync(self) -> Dict[str, Any]:
        """Run incremental data synchronization."""
        logger.info("Starting incremental data synchronization")
        start_time = datetime.now()
        
        try:
            # Refresh latest candles
            refresh_results = self.sync_service.refresh_latest_candles(
                symbol=self.symbol,
                timeframes=self.timeframes
            )
            
            # Detect and fill any new gaps
            gap_results = self.sync_service.detect_and_fill_gaps(
                symbol=self.symbol,
                timeframes=self.timeframes
            )
            
            # Validate current day data
            validation_results = {}
            for timeframe in self.timeframes:
                validation_results[timeframe] = self.sync_service.validate_current_day_data(
                    self.symbol, timeframe
                )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Prepare results
            sync_results = {
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "symbol": self.symbol,
                "timeframes": self.timeframes,
                "refresh_results": refresh_results,
                "gap_results": gap_results,
                "validation_results": validation_results,
                "status": "success"
            }
            
            # Log results
            self._log_sync_results(sync_results)
            
            logger.info(f"Incremental sync completed in {duration:.2f} seconds")
            return sync_results
            
        except Exception as e:
            logger.error(f"Incremental sync failed: {e}")
            return {
                "timestamp": start_time.isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def run_data_validation(self) -> Dict[str, Any]:
        """Run data validation and quality checks."""
        logger.info("Starting data validation")
        start_time = datetime.now()
        
        try:
            validation_results = {}
            data_quality_metrics = {}
            
            for timeframe in self.timeframes:
                # Validate current day data
                validation = self.sync_service.validate_current_day_data(
                    self.symbol, timeframe
                )
                validation_results[timeframe] = validation
                
                # Calculate data quality metrics
                quality_metrics = self._calculate_data_quality_metrics(
                    self.symbol, timeframe
                )
                data_quality_metrics[timeframe] = quality_metrics
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Prepare results
            validation_results = {
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "symbol": self.symbol,
                "timeframes": self.timeframes,
                "validation_results": validation_results,
                "data_quality_metrics": data_quality_metrics,
                "status": "success"
            }
            
            # Log results
            self._log_validation_results(validation_results)
            
            logger.info(f"Data validation completed in {duration:.2f} seconds")
            return validation_results
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {
                "timestamp": start_time.isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def _calculate_data_quality_metrics(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Calculate data quality metrics for a timeframe."""
        try:
            df = self.sync_service.load_ohlcv_data(symbol, timeframe)
            
            if df.empty:
                return {"error": "No data available"}
            
            # Convert timestamp to datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.sort_values('datetime')
            
            # Calculate metrics
            total_candles = len(df)
            date_range = (df['datetime'].max() - df['datetime'].min()).total_seconds() / 3600  # hours
            
            # Check for gaps
            interval_minutes = self.sync_service._get_interval_minutes(timeframe)
            expected_interval = pd.Timedelta(minutes=interval_minutes)
            
            gaps = 0
            for i in range(1, len(df)):
                current_time = df.iloc[i]['datetime']
                previous_time = df.iloc[i-1]['datetime']
                actual_interval = current_time - previous_time
                
                if actual_interval > expected_interval * 1.5:
                    gaps += 1
            
            # Calculate completeness
            expected_candles = int(date_range * 60 / interval_minutes)
            completeness = (total_candles / expected_candles) * 100 if expected_candles > 0 else 0
            
            # Check data freshness
            latest_candle = df['datetime'].iloc[-1]
            current_time = datetime.now()
            freshness_hours = (current_time - latest_candle).total_seconds() / 3600
            
            return {
                "total_candles": total_candles,
                "date_range_hours": date_range,
                "gaps_detected": gaps,
                "completeness_percentage": min(completeness, 100),
                "freshness_hours": freshness_hours,
                "is_fresh": freshness_hours < 2,  # Fresh if less than 2 hours old
                "latest_candle": latest_candle.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics for {timeframe}: {e}")
            return {"error": str(e)}
    
    def _log_sync_results(self, results: Dict[str, Any]):
        """Log sync results to structured log file."""
        log_entry = {
            "event_type": "sync_completed",
            "timestamp": results["timestamp"],
            "duration_seconds": results["duration_seconds"],
            "symbol": results["symbol"],
            "timeframes": results["timeframes"],
            "status": results["status"]
        }
        
        if results["status"] == "success":
            # Add success metrics
            log_entry.update({
                "download_results": results.get("download_results", {}),
                "gap_results": results.get("gap_results", {}),
                "validation_results": results.get("validation_results", {})
            })
        else:
            # Add error information
            log_entry.update({
                "error": results.get("error", "Unknown error")
            })
        
        # Write to structured log
        log_file = log_dir / "sync_metrics.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    
    def _log_validation_results(self, results: Dict[str, Any]):
        """Log validation results to structured log file."""
        log_entry = {
            "event_type": "validation_completed",
            "timestamp": results["timestamp"],
            "duration_seconds": results["duration_seconds"],
            "symbol": results["symbol"],
            "timeframes": results["timeframes"],
            "status": results["status"]
        }
        
        if results["status"] == "success":
            # Add validation metrics
            log_entry.update({
                "validation_results": results.get("validation_results", {}),
                "data_quality_metrics": results.get("data_quality_metrics", {})
            })
        else:
            # Add error information
            log_entry.update({
                "error": results.get("error", "Unknown error")
            })
        
        # Write to structured log
        log_file = log_dir / "validation_metrics.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


def main():
    """Main entry point for sync job."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data synchronization job")
    parser.add_argument("--mode", choices=["full", "incremental", "validation"], 
                       default="incremental", help="Sync mode")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol")
    parser.add_argument("--timeframes", default="1h,4h,1d,1w", help="Comma-separated timeframes")
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['TRADING_PAIRS'] = args.symbol
    os.environ['TIMEFRAMES'] = args.timeframes
    
    # Create and run sync job
    sync_job = SyncJob()
    
    if args.mode == "full":
        results = sync_job.run_full_sync()
    elif args.mode == "incremental":
        results = sync_job.run_incremental_sync()
    elif args.mode == "validation":
        results = sync_job.run_data_validation()
    
    # Print results
    print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if results["status"] == "success" else 1)


if __name__ == "__main__":
    main()
