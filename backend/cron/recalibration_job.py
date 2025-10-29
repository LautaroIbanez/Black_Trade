"""
Scheduled recalibration job for recommendation confidence monitoring and adjustment.

This job runs periodically to recalibrate recommendations and detect confidence deviations.
"""

import os
import sys
import logging
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from data.binance_client import BinanceClient
from data.sync_service import SyncService
from backend.services.strategy_registry import strategy_registry
from backend.services.recommendation_service import recommendation_service
from backtest.engine import BacktestEngine

# Configure logging
log_dir = Path(project_root) / "backend" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "recalibration.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class RecalibrationJob:
    """Scheduled job for recommendation recalibration and monitoring."""
    
    def __init__(self):
        """Initialize recalibration job."""
        self.binance_client = BinanceClient()
        self.sync_service = SyncService(self.binance_client)
        self.backtest_engine = BacktestEngine()
        self.symbol = os.getenv('TRADING_PAIRS', 'BTCUSDT')
        self.timeframes = os.getenv('TIMEFRAMES', '1h,4h,1d,1w').split(',')
        
        # Confidence deviation thresholds
        self.confidence_deviation_threshold = 0.3  # 30% deviation
        self.min_confidence_threshold = 0.1  # 10% minimum confidence
        
        logger.info(f"RecalibrationJob initialized for {self.symbol} on {self.timeframes}")
    
    def run_recalibration(self, profiles: List[str] = None) -> Dict[str, Any]:
        """Run full recalibration for all trading profiles."""
        if profiles is None:
            profiles = ['day_trading', 'swing', 'balanced', 'long_term']
        
        logger.info(f"Starting recalibration for profiles: {profiles}")
        start_time = datetime.now()
        
        try:
            # Load current data
            current_data = self._load_current_data()
            if not current_data:
                raise Exception("No current data available")
            
            # Load historical metrics
            historical_metrics = self._load_historical_metrics()
            
            # Run recalibration for each profile
            recalibration_results = {}
            for profile in profiles:
                logger.info(f"Recalibrating profile: {profile}")
                profile_result = self._recalibrate_profile(
                    profile, current_data, historical_metrics
                )
                recalibration_results[profile] = profile_result
            
            # Detect confidence deviations
            deviation_alerts = self._detect_confidence_deviations(recalibration_results)
            
            # Generate monitoring metrics
            monitoring_metrics = self._generate_monitoring_metrics(recalibration_results)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Prepare results
            results = {
                "timestamp": start_time.isoformat(),
                "duration_seconds": duration,
                "symbol": self.symbol,
                "timeframes": self.timeframes,
                "profiles": profiles,
                "recalibration_results": recalibration_results,
                "deviation_alerts": deviation_alerts,
                "monitoring_metrics": monitoring_metrics,
                "status": "success"
            }
            
            # Log results
            self._log_recalibration_results(results)
            
            logger.info(f"Recalibration completed in {duration:.2f} seconds")
            return results
            
        except Exception as e:
            logger.error(f"Recalibration failed: {e}")
            return {
                "timestamp": start_time.isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def _load_current_data(self) -> Optional[Dict[str, pd.DataFrame]]:
        """Load current market data for all timeframes."""
        current_data = {}
        
        for timeframe in self.timeframes:
            try:
                data = self.sync_service.load_ohlcv_data(self.symbol, timeframe)
                if not data.empty:
                    current_data[timeframe] = data
            except Exception as e:
                logger.error(f"Error loading data for {timeframe}: {e}")
                continue
        
        return current_data if current_data else None
    
    def _load_historical_metrics(self) -> Optional[Dict[str, List[Dict]]]:
        """Load historical backtest metrics."""
        try:
            # This would typically load from a persistent store
            # For now, we'll return None to use default behavior
            return None
        except Exception as e:
            logger.error(f"Error loading historical metrics: {e}")
            return None
    
    def _recalibrate_profile(self, profile: str, current_data: Dict[str, pd.DataFrame], 
                           historical_metrics: Optional[Dict[str, List[Dict]]]) -> Dict[str, Any]:
        """Recalibrate recommendations for a specific trading profile."""
        try:
            # Generate recommendation with current data
            recommendation = recommendation_service.generate_recommendation(
                current_data, historical_metrics, profile
            )
            
            # Calculate confidence metrics
            confidence_metrics = self._calculate_confidence_metrics(recommendation)
            
            # Check for confidence anomalies
            anomalies = self._detect_confidence_anomalies(recommendation, profile)
            
            return {
                "profile": profile,
                "action": recommendation.action,
                "confidence": recommendation.confidence,
                "primary_strategy": recommendation.primary_strategy,
                "supporting_strategies": recommendation.supporting_strategies,
                "confidence_metrics": confidence_metrics,
                "anomalies": anomalies,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error recalibrating profile {profile}: {e}")
            return {
                "profile": profile,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_confidence_metrics(self, recommendation) -> Dict[str, Any]:
        """Calculate detailed confidence metrics."""
        if not recommendation.strategy_details:
            return {}
        
        confidences = [s['confidence'] for s in recommendation.strategy_details]
        scores = [s['score'] for s in recommendation.strategy_details]
        weights = [s['weight'] for s in recommendation.strategy_details]
        
        return {
            "mean_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "max_confidence": max(confidences) if confidences else 0,
            "min_confidence": min(confidences) if confidences else 0,
            "confidence_std": pd.Series(confidences).std() if confidences else 0,
            "mean_score": sum(scores) / len(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "total_weight": sum(weights) if weights else 0,
            "strategy_count": len(recommendation.strategy_details)
        }
    
    def _detect_confidence_anomalies(self, recommendation, profile: str) -> List[Dict[str, Any]]:
        """Detect confidence anomalies for a recommendation."""
        anomalies = []
        
        # Check for very low confidence
        if recommendation.confidence < self.min_confidence_threshold:
            anomalies.append({
                "type": "low_confidence",
                "severity": "high",
                "value": recommendation.confidence,
                "threshold": self.min_confidence_threshold,
                "description": f"Confidence {recommendation.confidence:.2%} below minimum threshold"
            })
        
        # Check for confidence vs score mismatch
        if recommendation.strategy_details:
            confidences = [s['confidence'] for s in recommendation.strategy_details]
            scores = [s['score'] for s in recommendation.strategy_details]
            
            if confidences and scores:
                mean_confidence = sum(confidences) / len(confidences)
                mean_score = sum(scores) / len(scores)
                
                if abs(mean_confidence - mean_score) > 0.4:  # 40% difference
                    anomalies.append({
                        "type": "confidence_score_mismatch",
                        "severity": "medium",
                        "confidence": mean_confidence,
                        "score": mean_score,
                        "difference": abs(mean_confidence - mean_score),
                        "description": f"Large gap between confidence ({mean_confidence:.2%}) and historical score ({mean_score:.2%})"
                    })
        
        return anomalies
    
    def _detect_confidence_deviations(self, recalibration_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect confidence deviations across profiles."""
        alerts = []
        
        # Extract confidence values
        profile_confidences = {}
        for profile, result in recalibration_results.items():
            if 'confidence' in result:
                profile_confidences[profile] = result['confidence']
        
        if len(profile_confidences) < 2:
            return alerts
        
        # Calculate mean confidence across profiles
        mean_confidence = sum(profile_confidences.values()) / len(profile_confidences)
        
        # Check for significant deviations
        for profile, confidence in profile_confidences.items():
            deviation = abs(confidence - mean_confidence)
            if deviation > self.confidence_deviation_threshold:
                alerts.append({
                    "type": "confidence_deviation",
                    "profile": profile,
                    "confidence": confidence,
                    "mean_confidence": mean_confidence,
                    "deviation": deviation,
                    "severity": "high" if deviation > 0.5 else "medium",
                    "description": f"Profile {profile} confidence {confidence:.2%} deviates {deviation:.2%} from mean"
                })
        
        return alerts
    
    def _generate_monitoring_metrics(self, recalibration_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate monitoring metrics for dashboard."""
        metrics = {
            "total_profiles": len(recalibration_results),
            "successful_recalibrations": 0,
            "failed_recalibrations": 0,
            "total_anomalies": 0,
            "high_severity_alerts": 0,
            "profile_actions": {},
            "confidence_distribution": {},
            "strategy_usage": {}
        }
        
        for profile, result in recalibration_results.items():
            if 'error' not in result:
                metrics["successful_recalibrations"] += 1
                metrics["profile_actions"][profile] = result.get('action', 'UNKNOWN')
                metrics["confidence_distribution"][profile] = result.get('confidence', 0)
                
                # Count anomalies
                anomalies = result.get('anomalies', [])
                metrics["total_anomalies"] += len(anomalies)
                metrics["high_severity_alerts"] += len([a for a in anomalies if a.get('severity') == 'high'])
                
                # Track strategy usage
                primary_strategy = result.get('primary_strategy', 'Unknown')
                if primary_strategy not in metrics["strategy_usage"]:
                    metrics["strategy_usage"][primary_strategy] = 0
                metrics["strategy_usage"][primary_strategy] += 1
            else:
                metrics["failed_recalibrations"] += 1
        
        return metrics
    
    def _log_recalibration_results(self, results: Dict[str, Any]):
        """Log recalibration results to structured log file."""
        log_entry = {
            "event_type": "recalibration_completed",
            "timestamp": results["timestamp"],
            "duration_seconds": results["duration_seconds"],
            "symbol": results["symbol"],
            "profiles": results["profiles"],
            "status": results["status"],
            "successful_recalibrations": results["monitoring_metrics"]["successful_recalibrations"],
            "total_anomalies": results["monitoring_metrics"]["total_anomalies"],
            "deviation_alerts": len(results["deviation_alerts"])
        }
        
        if results["status"] == "success":
            # Add success metrics
            log_entry.update({
                "recalibration_results": results.get("recalibration_results", {}),
                "monitoring_metrics": results.get("monitoring_metrics", {})
            })
        else:
            # Add error information
            log_entry.update({
                "error": results.get("error", "Unknown error")
            })
        
        # Write to structured log
        log_file = log_dir / "recalibration_metrics.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")


def main():
    """Main entry point for recalibration job."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Recommendation recalibration job")
    parser.add_argument("--profiles", default="day_trading,swing,balanced,long_term", 
                       help="Comma-separated trading profiles")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading symbol")
    parser.add_argument("--timeframes", default="1h,4h,1d,1w", help="Comma-separated timeframes")
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['TRADING_PAIRS'] = args.symbol
    os.environ['TIMEFRAMES'] = args.timeframes
    
    # Parse profiles
    profiles = [p.strip() for p in args.profiles.split(',')]
    
    # Create and run recalibration job
    recalibration_job = RecalibrationJob()
    results = recalibration_job.run_recalibration(profiles)
    
    # Print results
    print(json.dumps(results, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if results["status"] == "success" else 1)


if __name__ == "__main__":
    main()
