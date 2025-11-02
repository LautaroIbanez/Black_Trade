"""Risk monitoring service that continuously checks limits and sends alerts."""
import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

from backend.risk.engine import RiskEngine
from backend.risk.alerts import AlertManager

logger = logging.getLogger(__name__)


class RiskMonitor:
    """Continuous risk monitoring service."""
    
    def __init__(
        self,
        risk_engine: RiskEngine,
        alert_manager: AlertManager,
        check_interval: int = 60,  # seconds
    ):
        """
        Initialize risk monitor.
        
        Args:
            risk_engine: Risk engine instance
            alert_manager: Alert manager instance
            check_interval: Interval between risk checks (seconds)
        """
        self.risk_engine = risk_engine
        self.alert_manager = alert_manager
        self.check_interval = check_interval
        self.running = False
        self.monitor_task = None
        
        # Track last alerts to avoid spam
        self.last_alerts = {}
        self.alert_cooldown = timedelta(minutes=5)  # 5 minutes cooldown
        
        self.logger = logging.getLogger(__name__)
    
    async def _check_limits(self):
        """Check risk limits and send alerts if violated."""
        try:
            metrics = self.risk_engine.get_risk_metrics()
            checks = self.risk_engine.check_risk_limits(metrics)
            
            # Check each limit
            for limit_name, check_data in checks.items():
                if check_data['violated']:
                    # Check cooldown
                    last_alert_time = self.last_alerts.get(limit_name)
                    if last_alert_time and (datetime.now() - last_alert_time) < self.alert_cooldown:
                        continue  # Skip if within cooldown
                    
                    # Send alert
                    self.alert_manager.alert_limit_violation(
                        limit_name=limit_name,
                        current_value=check_data['value'],
                        limit_value=check_data.get('limit', check_data.get('limit_pct', 0)),
                        metrics=metrics,
                    )
                    
                    # Update last alert time
                    self.last_alerts[limit_name] = datetime.now()
                    
                    # Special handling for critical alerts
                    if limit_name == 'drawdown':
                        self.alert_manager.alert_drawdown_critical(
                            drawdown_pct=metrics.current_drawdown_pct,
                            metrics=metrics,
                        )
                    elif limit_name == 'daily_loss':
                        self.alert_manager.alert_daily_loss_limit(
                            daily_pnl=metrics.daily_pnl,
                            limit_pct=self.risk_engine.risk_limits.daily_loss_limit_pct,
                            metrics=metrics,
                        )
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        self.logger.info(f"Risk monitor started (check interval: {self.check_interval}s)")
        
        while self.running:
            try:
                await self._check_limits()
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def start(self):
        """Start monitoring."""
        if self.running:
            self.logger.warning("Monitor already running")
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Risk monitor started")
    
    async def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Risk monitor stopped")

