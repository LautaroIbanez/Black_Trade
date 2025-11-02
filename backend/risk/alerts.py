"""Alert system for risk limit violations."""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Callable
from datetime import datetime
import json

import httpx

from backend.risk.engine import RiskMetrics

logger = logging.getLogger(__name__)


class AlertManager:
    """Manager for risk alerts and notifications."""
    
    def __init__(
        self,
        email_config: Optional[Dict] = None,
        slack_webhook: Optional[str] = None,
        websocket_callbacks: Optional[List[Callable]] = None,
    ):
        """
        Initialize alert manager.
        
        Args:
            email_config: Email configuration dict with smtp_host, smtp_port, username, password, from_email, to_emails
            slack_webhook: Slack webhook URL
            websocket_callbacks: List of callback functions for WebSocket alerts
        """
        self.email_config = email_config or {
            'smtp_host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from_email': os.getenv('SMTP_FROM'),
            'to_emails': os.getenv('SMTP_TO_EMAILS', '').split(','),
        }
        self.slack_webhook = slack_webhook or os.getenv('SLACK_WEBHOOK_URL')
        self.websocket_callbacks = websocket_callbacks or []
        
        self.logger = logging.getLogger(__name__)
    
    def send_email_alert(self, subject: str, message: str, html_message: Optional[str] = None) -> bool:
        """Send email alert."""
        if not all([self.email_config.get('smtp_host'), self.email_config.get('from_email'), 
                   self.email_config.get('to_emails')]):
            self.logger.warning("Email configuration incomplete, skipping email alert")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(self.email_config['to_emails'])
            
            # Plain text
            msg.attach(MIMEText(message, 'plain'))
            
            # HTML if provided
            if html_message:
                msg.attach(MIMEText(html_message, 'html'))
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_host'], self.email_config['smtp_port']) as server:
                server.starttls()
                if self.email_config.get('username') and self.email_config.get('password'):
                    server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
            
            self.logger.info(f"Email alert sent: {subject}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
            return False
    
    def send_slack_alert(self, title: str, message: str, severity: str = "warning") -> bool:
        """Send Slack alert via webhook."""
        if not self.slack_webhook:
            self.logger.warning("Slack webhook not configured, skipping Slack alert")
            return False
        
        # Color mapping
        colors = {
            'info': '#36a64f',      # Green
            'warning': '#ff9900',   # Orange
            'error': '#ff0000',     # Red
            'critical': '#8b0000',  # Dark red
        }
        color = colors.get(severity, '#808080')
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "Black Trade Risk Management",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }
        
        try:
            response = httpx.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            self.logger.info(f"Slack alert sent: {title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def send_websocket_alert(self, alert_data: Dict) -> None:
        """Send alert via WebSocket callbacks."""
        for callback in self.websocket_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                self.logger.error(f"Error in WebSocket callback: {e}")
    
    def alert_limit_violation(
        self,
        limit_name: str,
        current_value: float,
        limit_value: float,
        metrics: Optional[RiskMetrics] = None,
    ) -> None:
        """Send alert for risk limit violation."""
        severity = "error" if limit_name in ['drawdown', 'daily_loss'] else "warning"
        
        message = (
            f"RISK LIMIT VIOLATION: {limit_name.upper()}\n\n"
            f"Current Value: {current_value:.2f}\n"
            f"Limit: {limit_value:.2f}\n"
            f"Violation: {abs(current_value - limit_value):.2f}\n\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
        )
        
        if metrics:
            message += (
                f"\nCurrent Metrics:\n"
                f"  Total Capital: ${metrics.total_capital:,.2f}\n"
                f"  Equity: ${metrics.equity:,.2f}\n"
                f"  Exposure: {metrics.exposure_pct:.2f}%\n"
                f"  Drawdown: {metrics.current_drawdown_pct:.2f}%\n"
                f"  Daily P&L: ${metrics.daily_pnl:,.2f}\n"
            )
        
        subject = f"[RISK ALERT] {limit_name.upper()} Limit Violated"
        
        # Send via all channels
        self.send_email_alert(subject, message)
        self.send_slack_alert(f"Risk Limit Violation: {limit_name}", message, severity)
        
        # WebSocket alert
        alert_data = {
            'type': 'risk_limit_violation',
            'limit_name': limit_name,
            'current_value': current_value,
            'limit_value': limit_value,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics.__dict__ if metrics else None,
        }
        self.send_websocket_alert(alert_data)
        
        # Log
        self.logger.error(f"Risk limit violated: {limit_name} = {current_value:.2f} (limit: {limit_value:.2f})")
    
    def alert_drawdown_critical(self, drawdown_pct: float, metrics: RiskMetrics) -> None:
        """Alert for critical drawdown."""
        message = (
            f"CRITICAL DRAWDOWN ALERT\n\n"
            f"Current Drawdown: {drawdown_pct:.2f}%\n"
            f"Maximum Drawdown: {metrics.max_drawdown_pct:.2f}%\n"
            f"Peak Equity: ${metrics.peak_equity:,.2f}\n"
            f"Current Equity: ${metrics.equity:,.2f}\n"
            f"Loss: ${metrics.peak_equity - metrics.equity:,.2f}\n\n"
            f"IMMEDIATE ACTION REQUIRED\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
        )
        
        self.send_email_alert("[CRITICAL] Drawdown Alert", message)
        self.send_slack_alert("Critical Drawdown Detected", message, "critical")
        
        alert_data = {
            'type': 'critical_drawdown',
            'drawdown_pct': drawdown_pct,
            'metrics': metrics.__dict__,
            'timestamp': datetime.now().isoformat(),
        }
        self.send_websocket_alert(alert_data)
    
    def alert_daily_loss_limit(self, daily_pnl: float, limit_pct: float, metrics: RiskMetrics) -> None:
        """Alert for daily loss limit violation."""
        daily_pnl_pct = (abs(daily_pnl) / metrics.total_capital * 100) if metrics.total_capital > 0 else 0
        
        message = (
            f"DAILY LOSS LIMIT VIOLATED\n\n"
            f"Daily P&L: ${daily_pnl:,.2f} ({daily_pnl_pct:.2f}%)\n"
            f"Limit: {limit_pct:.2f}%\n"
            f"Current Capital: ${metrics.total_capital:,.2f}\n\n"
            f"Trading should be halted until review.\n"
            f"Timestamp: {datetime.now().isoformat()}\n"
        )
        
        self.send_email_alert("[CRITICAL] Daily Loss Limit", message)
        self.send_slack_alert("Daily Loss Limit Exceeded", message, "critical")
        
        alert_data = {
            'type': 'daily_loss_limit',
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl_pct,
            'limit_pct': limit_pct,
            'metrics': metrics.__dict__,
            'timestamp': datetime.now().isoformat(),
        }
        self.send_websocket_alert(alert_data)


# Global alert manager instance
alert_manager = AlertManager()

