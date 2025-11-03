"""Task scheduler for data ingestion."""
import logging
import os
import asyncio
from datetime import datetime
from typing import Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None

from backend.tasks.data_ingestion_task import DataIngestionTask
from backend.risk.update_task import RiskUpdateTask
from backend.api.routes.execution import get_execution_coordinator
from backend.execution.recommendation_task import RecommendationExecutionTask

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Scheduler for managing data ingestion tasks."""
    
    def __init__(self):
        """Initialize scheduler."""
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not installed. Install with: pip install apscheduler")
            self.scheduler = None
            return
        
        self.scheduler = AsyncIOScheduler()
        self.ingestion_task: Optional[DataIngestionTask] = None
        self.risk_task: Optional[RiskUpdateTask] = None
        self.reco_task: Optional[RecommendationExecutionTask] = None
        self.execution_job_scheduled: bool = False
        self.running = False
    
    def start_ingestion_task(self):
        """Start the data ingestion task."""
        if not APSCHEDULER_AVAILABLE:
            logger.error("APScheduler not available. Cannot start ingestion.")
            return
        
        if self.ingestion_task and self.ingestion_task.running:
            logger.info("Ingestion task already running")
            return
        
        logger.info("Starting data ingestion task...")
        
        # Create ingestion task
        ingestion_mode = os.getenv('INGESTION_MODE', 'websocket')
        symbols = os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')
        timeframes = os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')
        
        self.ingestion_task = DataIngestionTask(
            symbols=symbols,
            timeframes=timeframes,
            ingestion_mode=ingestion_mode,
        )
        
        # Start ingestion in background
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.ingestion_task.start())
        else:
            # If no event loop running, we'll start it when scheduler starts
            pass
        
        self.running = True
        logger.info("Data ingestion task prepared (will start with scheduler)")

    def schedule_risk_updates(self):
        """Schedule recurring risk updates and alerts."""
        if not APSCHEDULER_AVAILABLE or not self.scheduler:
            logger.warning("Scheduler not available. Skipping risk updates scheduling")
            return
        if self.risk_task is None:
            self.risk_task = RiskUpdateTask()
        # Add/update job
        try:
            # Replace existing job if present
            if self.scheduler.get_job("risk_update_job"):
                self.scheduler.remove_job("risk_update_job")
            self.scheduler.add_job(self._run_risk_update_once, IntervalTrigger(seconds=int(os.getenv('RISK_UPDATE_INTERVAL_SEC', '60'))), id="risk_update_job", max_instances=1, coalesce=True)
            logger.info("Risk update job scheduled")
        except Exception as e:
            logger.error(f"Failed to schedule risk update job: {e}")

    async def _run_risk_update_once(self):
        """Execute one risk update cycle (async wrapper)."""
        if self.risk_task is None:
            self.risk_task = RiskUpdateTask()
        try:
            await self.risk_task.run_once()
        except Exception as e:
            logger.error(f"Risk update job error: {e}")
    
    def stop_ingestion_task(self):
        """Stop the data ingestion task."""
        if self.ingestion_task and self.ingestion_task.running:
            logger.info("Stopping data ingestion task...")
            asyncio.create_task(self.ingestion_task.stop())
            self.running = False
            logger.info("Data ingestion task stopped")
    
    async def start_async(self):
        """Start the scheduler asynchronously."""
        if not APSCHEDULER_AVAILABLE or not self.scheduler:
            logger.warning("Scheduler not available")
            return
        
        # Start ingestion task
        self.start_ingestion_task()
        # Ensure risk updates are scheduled
        self.schedule_risk_updates()
        # Ensure execution processing is scheduled
        self.schedule_execution_processing()
        # Schedule auto-recommendation to orders if enabled
        self.schedule_recommendation_execution()
        
        # Ensure ingestion task is running
        if self.ingestion_task:
            await self.ingestion_task.start()
    
    def start(self):
        """Start the scheduler (synchronous wrapper)."""
        if not APSCHEDULER_AVAILABLE or not self.scheduler:
            logger.warning("Scheduler not available, starting ingestion directly")
            # Start ingestion without scheduler
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_async())
            return
        
        # Start scheduler
        self.scheduler.start()
        logger.info("Ingestion scheduler started")
        
        # Start ingestion task in background
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.start_async())
            else:
                loop.run_until_complete(self.start_async())
        except Exception as e:
            logger.error(f"Error starting ingestion task: {e}")

    def schedule_execution_processing(self):
        """Schedule background processing of pending orders."""
        if not APSCHEDULER_AVAILABLE or not self.scheduler:
            logger.warning("Scheduler not available. Skipping execution scheduling")
            return
        try:
            if self.scheduler.get_job("execution_process_job"):
                self.scheduler.remove_job("execution_process_job")
            interval = int(os.getenv('EXECUTION_PROCESS_INTERVAL_SEC', '3'))
            self.scheduler.add_job(self._run_execution_once, IntervalTrigger(seconds=interval), id="execution_process_job", max_instances=1, coalesce=True)
            self.execution_job_scheduled = True
            logger.info("Execution processing job scheduled")
        except Exception as e:
            logger.error(f"Failed to schedule execution processing: {e}")

    async def _run_execution_once(self):
        """One cycle of processing pending orders and timeouts."""
        try:
            coordinator = get_execution_coordinator()
            engine = coordinator.execution_engine
            await engine.process_pending_orders()
            engine.check_timeouts()
        except Exception as e:
            logger.error(f"Execution processing error: {e}")

    def schedule_recommendation_execution(self):
        """Schedule automatic conversion of recommendations to orders."""
        if not APSCHEDULER_AVAILABLE or not self.scheduler:
            return
        if os.getenv('ENABLE_AUTO_ORDERS', 'false').lower() != 'true':
            return
        try:
            if self.reco_task is None:
                self.reco_task = RecommendationExecutionTask()
            if self.scheduler.get_job("recommendation_exec_job"):
                self.scheduler.remove_job("recommendation_exec_job")
            interval = int(os.getenv('AUTO_ORDER_INTERVAL_SEC', '30'))
            self.scheduler.add_job(self._run_recommendation_once, IntervalTrigger(seconds=interval), id="recommendation_exec_job", max_instances=1, coalesce=True)
            logger.info("Recommendation→Order job scheduled")
        except Exception as e:
            logger.error(f"Failed to schedule recommendation job: {e}")

    async def _run_recommendation_once(self):
        try:
            if self.reco_task is None:
                self.reco_task = RecommendationExecutionTask()
            await self.reco_task.run_once()
        except Exception as e:
            logger.error(f"Recommendation job error: {e}")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler:
            self.stop_ingestion_task()
            self.scheduler.shutdown()
            logger.info("Ingestion scheduler shutdown")


# Global scheduler instance
_scheduler: Optional[IngestionScheduler] = None


def get_scheduler() -> Optional[IngestionScheduler]:
    """Get global scheduler instance."""
    return _scheduler


def init_scheduler() -> Optional[IngestionScheduler]:
    """Initialize and start the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = IngestionScheduler()
    return _scheduler

