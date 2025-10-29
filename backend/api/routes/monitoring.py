"""
Monitoring API routes for recalibration metrics and alerts.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

# Log directory
project_root = Path(__file__).parent.parent.parent.parent
log_dir = project_root / "backend" / "logs"


class MonitoringMetrics(BaseModel):
    """Monitoring metrics response."""
    timestamp: str
    total_profiles: int
    successful_recalibrations: int
    failed_recalibrations: int
    total_anomalies: int
    high_severity_alerts: int
    profile_actions: Dict[str, str]
    confidence_distribution: Dict[str, float]
    strategy_usage: Dict[str, int]


class RecalibrationAlert(BaseModel):
    """Recalibration alert."""
    type: str
    severity: str
    description: str
    timestamp: str
    profile: Optional[str] = None
    value: Optional[float] = None
    threshold: Optional[float] = None


class MonitoringResponse(BaseModel):
    """Complete monitoring response."""
    latest_metrics: Optional[MonitoringMetrics]
    recent_alerts: List[RecalibrationAlert]
    system_health: str
    last_recalibration: Optional[str]


@router.get("/monitoring/metrics", response_model=MonitoringResponse)
async def get_monitoring_metrics(
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back for metrics")
) -> MonitoringResponse:
    """Get latest monitoring metrics and alerts."""
    try:
        # Load latest metrics
        latest_metrics = _load_latest_metrics()
        
        # Load recent alerts
        recent_alerts = _load_recent_alerts(hours_back)
        
        # Determine system health
        system_health = _determine_system_health(latest_metrics, recent_alerts)
        
        # Get last recalibration time
        last_recalibration = _get_last_recalibration_time()
        
        return MonitoringResponse(
            latest_metrics=latest_metrics,
            recent_alerts=recent_alerts,
            system_health=system_health,
            last_recalibration=last_recalibration
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading monitoring metrics: {str(e)}")


@router.get("/monitoring/alerts", response_model=List[RecalibrationAlert])
async def get_recent_alerts(
    hours_back: int = Query(24, ge=1, le=168, description="Hours to look back for alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity level")
) -> List[RecalibrationAlert]:
    """Get recent recalibration alerts."""
    try:
        alerts = _load_recent_alerts(hours_back)
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        return alerts
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading alerts: {str(e)}")


@router.get("/monitoring/health")
async def get_system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    try:
        # Load latest metrics
        latest_metrics = _load_latest_metrics()
        
        # Load recent alerts
        recent_alerts = _load_recent_alerts(24)
        
        # Determine health status
        health_status = _determine_system_health(latest_metrics, recent_alerts)
        
        # Calculate health score (0-100)
        health_score = _calculate_health_score(latest_metrics, recent_alerts)
        
        # Get system status details
        status_details = _get_system_status_details(latest_metrics, recent_alerts)
        
        return {
            "status": health_status,
            "health_score": health_score,
            "timestamp": datetime.now().isoformat(),
            "details": status_details
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking system health: {str(e)}")


def _load_latest_metrics() -> Optional[MonitoringMetrics]:
    """Load the latest monitoring metrics."""
    try:
        log_file = log_dir / "recalibration_metrics.jsonl"
        if not log_file.exists():
            return None
        
        # Read the last line (most recent entry)
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if not lines:
                return None
            
            # Parse the last line
            last_entry = json.loads(lines[-1].strip())
            
            if last_entry.get("event_type") != "recalibration_completed":
                return None
            
            monitoring_metrics = last_entry.get("monitoring_metrics", {})
            
            return MonitoringMetrics(
                timestamp=last_entry["timestamp"],
                total_profiles=monitoring_metrics.get("total_profiles", 0),
                successful_recalibrations=monitoring_metrics.get("successful_recalibrations", 0),
                failed_recalibrations=monitoring_metrics.get("failed_recalibrations", 0),
                total_anomalies=monitoring_metrics.get("total_anomalies", 0),
                high_severity_alerts=monitoring_metrics.get("high_severity_alerts", 0),
                profile_actions=monitoring_metrics.get("profile_actions", {}),
                confidence_distribution=monitoring_metrics.get("confidence_distribution", {}),
                strategy_usage=monitoring_metrics.get("strategy_usage", {})
            )
            
    except Exception as e:
        print(f"Error loading latest metrics: {e}")
        return None


def _load_recent_alerts(hours_back: int) -> List[RecalibrationAlert]:
    """Load recent alerts from log files."""
    alerts = []
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    try:
        log_file = log_dir / "recalibration_metrics.jsonl"
        if not log_file.exists():
            return alerts
        
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_time = datetime.fromisoformat(entry["timestamp"])
                    
                    if entry_time < cutoff_time:
                        continue
                    
                    # Extract alerts from recalibration results
                    if entry.get("event_type") == "recalibration_completed":
                        recalibration_results = entry.get("recalibration_results", {})
                        deviation_alerts = entry.get("deviation_alerts", [])
                        
                        # Process deviation alerts
                        for alert_data in deviation_alerts:
                            alerts.append(RecalibrationAlert(
                                type=alert_data["type"],
                                severity=alert_data["severity"],
                                description=alert_data["description"],
                                timestamp=entry["timestamp"],
                                profile=alert_data.get("profile"),
                                value=alert_data.get("confidence"),
                                threshold=alert_data.get("mean_confidence")
                            ))
                        
                        # Process profile-specific anomalies
                        for profile, result in recalibration_results.items():
                            if isinstance(result, dict) and "anomalies" in result:
                                for anomaly in result["anomalies"]:
                                    alerts.append(RecalibrationAlert(
                                        type=anomaly["type"],
                                        severity=anomaly["severity"],
                                        description=anomaly["description"],
                                        timestamp=entry["timestamp"],
                                        profile=profile,
                                        value=anomaly.get("value"),
                                        threshold=anomaly.get("threshold")
                                    ))
                
                except (json.JSONDecodeError, KeyError) as e:
                    continue
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
    except Exception as e:
        print(f"Error loading recent alerts: {e}")
    
    return alerts


def _determine_system_health(metrics: Optional[MonitoringMetrics], alerts: List[RecalibrationAlert]) -> str:
    """Determine overall system health status."""
    if not metrics:
        return "unknown"
    
    # Check for high severity alerts
    high_severity_count = len([a for a in alerts if a.severity == "high"])
    if high_severity_count > 0:
        return "critical"
    
    # Check failure rate
    total_recalibrations = metrics.successful_recalibrations + metrics.failed_recalibrations
    if total_recalibrations > 0:
        failure_rate = metrics.failed_recalibrations / total_recalibrations
        if failure_rate > 0.5:  # More than 50% failures
            return "degraded"
        elif failure_rate > 0.2:  # More than 20% failures
            return "warning"
    
    # Check anomaly rate
    if metrics.total_anomalies > metrics.successful_recalibrations * 0.5:
        return "warning"
    
    return "healthy"


def _calculate_health_score(metrics: Optional[MonitoringMetrics], alerts: List[RecalibrationAlert]) -> int:
    """Calculate health score (0-100)."""
    if not metrics:
        return 0
    
    score = 100
    
    # Deduct for failures
    total_recalibrations = metrics.successful_recalibrations + metrics.failed_recalibrations
    if total_recalibrations > 0:
        failure_rate = metrics.failed_recalibrations / total_recalibrations
        score -= int(failure_rate * 50)  # Up to 50 points for failures
    
    # Deduct for high severity alerts
    high_severity_count = len([a for a in alerts if a.severity == "high"])
    score -= high_severity_count * 20  # 20 points per high severity alert
    
    # Deduct for medium severity alerts
    medium_severity_count = len([a for a in alerts if a.severity == "medium"])
    score -= medium_severity_count * 5  # 5 points per medium severity alert
    
    # Deduct for anomalies
    if metrics.total_anomalies > 0:
        anomaly_penalty = min(metrics.total_anomalies * 2, 20)  # Up to 20 points for anomalies
        score -= anomaly_penalty
    
    return max(0, score)


def _get_system_status_details(metrics: Optional[MonitoringMetrics], alerts: List[RecalibrationAlert]) -> Dict[str, Any]:
    """Get detailed system status information."""
    if not metrics:
        return {"error": "No metrics available"}
    
    return {
        "recalibration_status": {
            "total_profiles": metrics.total_profiles,
            "successful": metrics.successful_recalibrations,
            "failed": metrics.failed_recalibrations,
            "success_rate": f"{(metrics.successful_recalibrations / max(metrics.successful_recalibrations + metrics.failed_recalibrations, 1)) * 100:.1f}%"
        },
        "alert_summary": {
            "total_alerts": len(alerts),
            "high_severity": len([a for a in alerts if a.severity == "high"]),
            "medium_severity": len([a for a in alerts if a.severity == "medium"]),
            "low_severity": len([a for a in alerts if a.severity == "low"])
        },
        "anomaly_summary": {
            "total_anomalies": metrics.total_anomalies,
            "high_severity_alerts": metrics.high_severity_alerts
        },
        "profile_distribution": metrics.profile_actions,
        "strategy_usage": metrics.strategy_usage
    }


def _get_last_recalibration_time() -> Optional[str]:
    """Get the timestamp of the last recalibration."""
    try:
        log_file = log_dir / "recalibration_metrics.jsonl"
        if not log_file.exists():
            return None
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if not lines:
                return None
            
            # Find the last recalibration entry
            for line in reversed(lines):
                try:
                    entry = json.loads(line.strip())
                    if entry.get("event_type") == "recalibration_completed":
                        return entry["timestamp"]
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return None
        
    except Exception as e:
        print(f"Error getting last recalibration time: {e}")
        return None
