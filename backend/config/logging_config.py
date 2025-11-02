"""Logging configuration for audit compliance."""
import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional
import json


class AuditLogger:
    """Logger for audit trail compliant with regulatory requirements."""
    
    def __init__(self, log_dir: str = "logs/audit"):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create audit logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        # Create file handler with rotation
        log_file = self.log_dir / "audit.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=30,  # Keep 30 days
        )
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S UTC'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        
        # Also log to JSON for easier parsing
        self.json_log_file = self.log_dir / "audit.jsonl"
        self.json_handler = logging.handlers.RotatingFileHandler(
            self.json_log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=30,
        )
        self.json_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(self.json_handler)
    
    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        action: str = "",
        resource: str = "",
        details: dict = None,
        ip_address: Optional[str] = None,
        success: bool = True,
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (login, order_execution, risk_change, etc.)
            user_id: User ID who performed the action
            action: Action performed
            resource: Resource affected
            details: Additional details
            ip_address: IP address of requester
            success: Whether action was successful
        """
        event = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'event_type': event_type,
            'user_id': user_id or 'system',
            'action': action,
            'resource': resource,
            'details': details or {},
            'ip_address': ip_address,
            'success': success,
        }
        
        # Sanitize sensitive data (don't log passwords, API keys, etc.)
        event = self._sanitize_event(event)
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, json.dumps(event))
    
    def _sanitize_event(self, event: dict) -> dict:
        """Remove sensitive information from event."""
        sensitive_keys = ['password', 'api_key', 'secret', 'token', 'credentials']
        
        def sanitize_dict(d):
            if isinstance(d, dict):
                return {
                    k: '***REDACTED***' if any(key in k.lower() for key in sensitive_keys)
                    else sanitize_dict(v) if isinstance(v, (dict, list)) else v
                    for k, v in d.items()
                }
            elif isinstance(d, list):
                return [sanitize_dict(item) for item in d]
            return d
        
        return sanitize_dict(event)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add any extra fields
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        return json.dumps(log_data)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        log_dir = os.getenv('AUDIT_LOG_DIR', 'logs/audit')
        _audit_logger = AuditLogger(log_dir)
    return _audit_logger


def configure_logging():
    """Configure application logging with audit compliance."""
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for application logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=30,
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Initialize audit logger
    get_audit_logger()

