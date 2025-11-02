"""Alert system for system health and performance issues."""
import logging
import os
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum

import httpx

from backend.observability.metrics import SystemMetrics, get_metrics_collector
from backend.risk.alerts import AlertManager

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertType(str, Enum):
    """Alert types."""
    HIGH_LATENCY = "high_latency"
    HIGH_ERROR_RATE = "high_error_rate"
    LOW_THROUGHPUT = "low_throughput"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    SERVICE_DOWN = "service_down"
    DATABASE_CONNECTION = "database_connection"
    ORDER_EXECUTION_FAILURE = "order_execution_failure"
    RISK_LIMIT_VIOLATION = "risk_limit_violation"
    STRATEGY_DEGRADATION = "strategy_degradation"


@dataclass
class Alert:
    """Alert data structure."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    details: Dict
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class ObservabilityAlertManager:
    """Manager for system observability alerts."""
    
    def __init__(
        self,
        slack_webhook: Optional[str] = None,
        pagerduty_integration_key: Optional[str] = None,
        email_config: Optional[Dict] = None,
        alert_thresholds: Optional[Dict] = None,
    ):
        """
        Initialize observability alert manager.
        
        Args:
            slack_webhook: Slack webhook URL
            pagerduty_integration_key: PagerDuty integration key
            email_config: Email configuration
            alert_thresholds: Custom alert thresholds
        """
        self.slack_webhook = slack_webhook or os.getenv("SLACK_WEBHOOK_URL")
        self.pagerduty_key = pagerduty_integration_key or os.getenv("PAGERDUTY_INTEGRATION_KEY")
        
        # Reuse risk alert manager for email
        self.risk_alert_manager = AlertManager(
            email_config=email_config,
            slack_webhook=self.slack_webhook,
        )
        
        # Default thresholds
        self.thresholds = alert_thresholds or {
            'latency_p95_ms': 1000.0,  # 1 second
            'latency_p99_ms': 2000.0,  # 2 seconds
            'error_rate_percent': 5.0,
            'cpu_usage_percent': 80.0,
            'memory_usage_mb': 2048.0,  # 2GB
            'order_rejection_rate_percent': 10.0,
        }
        
        # Alert history
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        self.logger = logging.getLogger(__name__)
    
    def check_metrics(self, metrics: SystemMetrics) -> List[Alert]:
        """
        Check metrics against thresholds and generate alerts.
        
        Args:
            metrics: Current system metrics
            
        Returns:
            List of new alerts
        """
        new_alerts = []
        
        # Check latency
        if metrics.api_latency_p95 > self.thresholds['latency_p95_ms']:
            alert = self._create_alert(
                AlertType.HIGH_LATENCY,
                AlertSeverity.WARNING,
                "High API Latency Detected",
                f"P95 latency is {metrics.api_latency_p95:.2f}ms (threshold: {self.thresholds['latency_p95_ms']}ms)",
                {'latency_p95': metrics.api_latency_p95, 'threshold': self.thresholds['latency_p95_ms']},
            )
            new_alerts.append(alert)
        
        if metrics.api_latency_p99 > self.thresholds['latency_p99_ms']:
            alert = self._create_alert(
                AlertType.HIGH_LATENCY,
                AlertSeverity.CRITICAL,
                "Critical API Latency",
                f"P99 latency is {metrics.api_latency_p99:.2f}ms (threshold: {self.thresholds['latency_p99_ms']}ms)",
                {'latency_p99': metrics.api_latency_p99, 'threshold': self.thresholds['latency_p99_ms']},
            )
            new_alerts.append(alert)
        
        # Check error rate
        if metrics.error_rate > self.thresholds['error_rate_percent']:
            alert = self._create_alert(
                AlertType.HIGH_ERROR_RATE,
                AlertSeverity.CRITICAL,
                "High Error Rate",
                f"Error rate is {metrics.error_rate:.2f}% (threshold: {self.thresholds['error_rate_percent']}%)",
                {'error_rate': metrics.error_rate, 'threshold': self.thresholds['error_rate_percent']},
            )
            new_alerts.append(alert)
        
        # Check CPU usage
        if metrics.cpu_usage_percent > self.thresholds['cpu_usage_percent']:
            alert = self._create_alert(
                AlertType.HIGH_CPU,
                AlertSeverity.WARNING,
                "High CPU Usage",
                f"CPU usage is {metrics.cpu_usage_percent:.2f}% (threshold: {self.thresholds['cpu_usage_percent']}%)",
                {'cpu_usage': metrics.cpu_usage_percent, 'threshold': self.thresholds['cpu_usage_percent']},
            )
            new_alerts.append(alert)
        
        # Check memory usage
        if metrics.memory_usage_mb > self.thresholds['memory_usage_mb']:
            alert = self._create_alert(
                AlertType.HIGH_MEMORY,
                AlertSeverity.WARNING,
                "High Memory Usage",
                f"Memory usage is {metrics.memory_usage_mb:.2f}MB (threshold: {self.thresholds['memory_usage_mb']}MB)",
                {'memory_usage': metrics.memory_usage_mb, 'threshold': self.thresholds['memory_usage_mb']},
            )
            new_alerts.append(alert)
        
        # Check order rejection rate
        if metrics.order_rejection_rate > self.thresholds['order_rejection_rate_percent']:
            alert = self._create_alert(
                AlertType.ORDER_EXECUTION_FAILURE,
                AlertSeverity.WARNING,
                "High Order Rejection Rate",
                f"Order rejection rate is {metrics.order_rejection_rate:.2f}% (threshold: {self.thresholds['order_rejection_rate_percent']}%)",
                {'rejection_rate': metrics.order_rejection_rate, 'threshold': self.thresholds['order_rejection_rate_percent']},
            )
            new_alerts.append(alert)
        
        # Process alerts
        for alert in new_alerts:
            self._process_alert(alert)
        
        return new_alerts
    
    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        details: Dict,
    ) -> Alert:
        """Create alert object."""
        alert_id = f"{alert_type.value}_{datetime.now().timestamp()}"
        
        return Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            details=details,
            timestamp=datetime.now(),
        )
    
    def _process_alert(self, alert: Alert):
        """Process and send alert."""
        # Check if alert already exists
        existing_alert_key = f"{alert.alert_type.value}"
        if existing_alert_key in self.active_alerts:
            # Alert already active, skip duplicate
            return
        
        # Store alert
        self.active_alerts[existing_alert_key] = alert
        self.alert_history.append(alert)
        
        # Send notifications based on severity
        if alert.severity == AlertSeverity.CRITICAL:
            self._send_critical_alert(alert)
        elif alert.severity == AlertSeverity.WARNING:
            self._send_warning_alert(alert)
        else:
            self._send_info_alert(alert)
        
        self.logger.warning(f"Alert triggered: {alert.title} - {alert.message}")
    
    def _send_critical_alert(self, alert: Alert):
        """Send critical alert via all channels."""
        # Slack
        if self.slack_webhook:
            self._send_slack_alert(alert, color="danger")
        
        # PagerDuty
        if self.pagerduty_key:
            self._send_pagerduty_alert(alert)
        
        # Email
        self.risk_alert_manager.send_email_alert(
            subject=f"[CRITICAL] {alert.title}",
            message=alert.message,
        )
    
    def _send_warning_alert(self, alert: Alert):
        """Send warning alert via Slack."""
        if self.slack_webhook:
            self._send_slack_alert(alert, color="warning")
    
    def _send_info_alert(self, alert: Alert):
        """Send info alert (usually just logged)."""
        self.logger.info(f"Alert: {alert.title} - {alert.message}")
    
    def _send_slack_alert(self, alert: Alert, color: str = "warning"):
        """Send alert to Slack."""
        if not self.slack_webhook:
            return
        
        try:
            payload = {
                "attachments": [{
                    "color": color,
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Type", "value": alert.alert_type.value, "short": True},
                        {"title": "Timestamp", "value": alert.timestamp.isoformat(), "short": False},
                    ],
                    "footer": "Black Trade Observability",
                    "ts": alert.timestamp.timestamp(),
                }]
            }
            
            import httpx
            with httpx.Client() as client:
                response = client.post(self.slack_webhook, json=payload, timeout=5)
                response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_pagerduty_alert(self, alert: Alert):
        """Send alert to PagerDuty."""
        if not self.pagerduty_key:
            return
        
        try:
            payload = {
                "routing_key": self.pagerduty_key,
                "event_action": "trigger",
                "payload": {
                    "summary": alert.title,
                    "severity": alert.severity.value,
                    "source": "black-trade",
                    "custom_details": {
                        "message": alert.message,
                        "alert_type": alert.alert_type.value,
                        **alert.details,
                    },
                },
            }
            
            import httpx
            with httpx.Client() as client:
                response = client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                    timeout=5,
                )
                response.raise_for_status()
        except Exception as e:
            self.logger.error(f"Failed to send PagerDuty alert: {e}")
    
    def resolve_alert(self, alert_type: AlertType):
        """Resolve an alert."""
        alert_key = f"{alert_type.value}"
        if alert_key in self.active_alerts:
            alert = self.active_alerts[alert_key]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            del self.active_alerts[alert_key]
            self.logger.info(f"Alert resolved: {alert.title}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get list of active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return self.alert_history[-limit:]

