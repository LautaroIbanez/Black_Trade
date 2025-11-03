"""Message processor for ingesting candles into database."""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import time

from backend.repositories.ohlcv_repository import OHLCVRepository
from backend.repositories.ingestion_repository import IngestionRepository
from backend.services.signal_computation import SignalComputationService
from backend.observability.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Process incoming candle messages and persist to database."""
    
    def __init__(self, batch_size: int = 100, batch_timeout: float = 1.0):
        """
        Initialize message processor.
        
        Args:
            batch_size: Number of candles to batch before inserting
            batch_timeout: Maximum time to wait before flushing batch (seconds)
        """
        self.ohlcv_repo = OHLCVRepository()
        self.ingestion_repo = IngestionRepository()
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.signal_service = SignalComputationService()
        
        # Batch buffer
        self.batch_buffer: List[Dict] = []
        self.last_flush_time = time.time()
        self.processing_lock = asyncio.Lock()
    
    async def process_candle(self, candle: Dict):
        """
        Process a single candle message.
        
        Args:
            candle: Candle dictionary with keys: symbol, timeframe, timestamp, open, high, low, close, volume, etc.
        """
        async with self.processing_lock:
            # Add to batch buffer
            self.batch_buffer.append(candle)
            
            # Check if we should flush
            should_flush = (
                len(self.batch_buffer) >= self.batch_size or
                (time.time() - self.last_flush_time) >= self.batch_timeout
            )
            
            if should_flush:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush batch buffer to database."""
        if not self.batch_buffer:
            return
        
        batch = self.batch_buffer.copy()
        self.batch_buffer.clear()
        self.last_flush_time = time.time()
        
        try:
            # Group by symbol/timeframe for status updates
            processed_groups = {}
            
            # Save batch
            saved_count = self.ohlcv_repo.save_batch(batch)
            
            # Update ingestion status for each unique symbol/timeframe
            for candle in batch:
                key = f"{candle['symbol']}_{candle.get('timeframe', 'N/A')}"
                if key not in processed_groups:
                    processed_groups[key] = {
                        'symbol': candle['symbol'],
                        'timeframe': candle.get('timeframe', 'N/A'),
                        'latest_timestamp': candle['timestamp'],
                        'count': 0
                    }
                processed_groups[key]['count'] += 1
                if candle['timestamp'] > processed_groups[key]['latest_timestamp']:
                    processed_groups[key]['latest_timestamp'] = candle['timestamp']
            
            # Update statuses
            for group_key, group_data in processed_groups.items():
                self.ingestion_repo.update_status(
                    symbol=group_data['symbol'],
                    timeframe=group_data['timeframe'],
                    status_data={
                        'last_ingested_timestamp': group_data['latest_timestamp'],
                        'last_ingested_at': datetime.utcnow(),
                        'ingestion_mode': 'websocket',  # or 'polling'
                        'status': 'active',
                    }
                )
                
                # Record metrics
                latency_ms = int((time.time() * 1000) - group_data['latest_timestamp'])
                self.ingestion_repo.record_metric(
                    symbol=group_data['symbol'],
                    timeframe=group_data['timeframe'],
                    metric_type='latency',
                    metric_value=latency_ms
                )
                self.ingestion_repo.record_metric(
                    symbol=group_data['symbol'],
                    timeframe=group_data['timeframe'],
                    metric_type='throughput',
                    metric_value=group_data['count']
                )
            
            logger.info(f"Processed batch: {saved_count} candles across {len(processed_groups)} symbol/timeframe groups")

            # Trigger signal computation asynchronously for impacted timeframes
            try:
                impacted_timeframes = [g['timeframe'] for g in processed_groups.values() if g.get('timeframe')]
                async def _run_signals():
                    t0 = time.time()
                    ok = await self.signal_service.compute_and_store(impacted_timeframes)
                    try:
                        latency_ms = int((time.time() - t0) * 1000)
                        get_metrics_collector().record_strategy_metric('system', 'generation_time', latency_ms)
                    except Exception:
                        pass
                    # Record freshness timestamp via publisher cache
                    if ok:
                        try:
                            from backend.recommendation.live_recommendations_service import live_recommendations_service
                            _ = live_recommendations_service.get_freshness()
                        except Exception:
                            pass
                asyncio.create_task(_run_signals())
            except Exception as e:
                logger.error(f"Failed to trigger signal computation: {e}")
            
        except Exception as e:
            logger.error(f"Error flushing batch: {e}")
            # Re-add batch to buffer for retry (simple approach, could use queue)
            self.batch_buffer.extend(batch)
    
    async def flush(self):
        """Manually flush any remaining batch."""
        async with self.processing_lock:
            await self._flush_batch()
    
    async def process_batch(self, candles: List[Dict]):
        """Process a batch of candles directly (bypass batching)."""
        try:
            saved_count = self.ohlcv_repo.save_batch(candles)
            logger.info(f"Processed direct batch: {saved_count} candles")
            return saved_count
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise

