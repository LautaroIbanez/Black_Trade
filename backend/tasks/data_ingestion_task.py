"""Main data ingestion task orchestrator."""
import asyncio
import logging
import os
from typing import List, Optional, Dict

from backend.ingestion.websocket_consumer import BinanceWebSocketConsumer
from backend.ingestion.polling_consumer import PollingConsumer
from backend.ingestion.processor import MessageProcessor
from backend.repositories.ingestion_repository import IngestionRepository

logger = logging.getLogger(__name__)


class DataIngestionTask:
    """Orchestrates real-time data ingestion."""
    
    def __init__(self, symbols: Optional[List[str]] = None, 
                 timeframes: Optional[List[str]] = None,
                 ingestion_mode: str = 'websocket'):
        """
        Initialize ingestion task.
        
        Args:
            symbols: List of trading pairs (default from env)
            timeframes: List of intervals (default from env)
            ingestion_mode: 'websocket' or 'polling'
        """
        self.symbols = symbols or os.getenv('TRADING_PAIRS', 'BTCUSDT').split(',')
        self.timeframes = timeframes or os.getenv('TIMEFRAMES', '15m,1h,4h,1d').split(',')
        self.ingestion_mode = ingestion_mode.lower()
        
        # Initialize processor
        self.processor = MessageProcessor(batch_size=100, batch_timeout=1.0)
        
        # Initialize consumers
        self.websocket_consumer = None
        self.polling_consumer = None
        
        # Status
        self.running = False
        self.ingestion_repo = IngestionRepository()
    
    async def _message_callback(self, candle: dict):
        """Callback for processing incoming candles."""
        await self.processor.process_candle(candle)
    
    async def start_websocket(self):
        """Start WebSocket ingestion."""
        logger.info(f"Starting WebSocket ingestion for {self.symbols} on {self.timeframes}")
        
        try:
            self.websocket_consumer = BinanceWebSocketConsumer(
                symbols=self.symbols,
                timeframes=self.timeframes,
                message_callback=self._message_callback,
                reconnect_delay=5
            )
            
            # Start consumer (this will run until stopped)
            await self.websocket_consumer.start()
            
        except Exception as e:
            logger.error(f"WebSocket ingestion failed: {e}")
            # Fallback to polling
            logger.info("Falling back to polling mode")
            await self.start_polling()
    
    async def start_polling(self):
        """Start REST polling ingestion."""
        logger.info(f"Starting polling ingestion for {self.symbols} on {self.timeframes}")
        
        self.polling_consumer = PollingConsumer(
            symbols=self.symbols,
            timeframes=self.timeframes,
            message_callback=self._message_callback
        )
        
        await self.polling_consumer.start()
    
    async def start(self):
        """Start ingestion based on configured mode."""
        self.running = True
        
        # Update statuses
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                self.ingestion_repo.update_status(
                    symbol=symbol,
                    timeframe=timeframe,
                    status_data={
                        'ingestion_mode': self.ingestion_mode,
                        'status': 'starting',
                    }
                )
        
        try:
            if self.ingestion_mode == 'websocket':
                await self.start_websocket()
            else:
                await self.start_polling()
        except KeyboardInterrupt:
            logger.info("Ingestion stopped by user")
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            # Update statuses to error
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    self.ingestion_repo.update_status(
                        symbol=symbol,
                        timeframe=timeframe,
                        status_data={
                            'status': 'error',
                            'error_message': str(e),
                        }
                    )
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop ingestion."""
        self.running = False
        
        if self.websocket_consumer:
            await self.websocket_consumer.disconnect()
        
        if self.polling_consumer:
            self.polling_consumer.stop()
        
        # Flush any remaining batch
        await self.processor.flush()
        
        logger.info("Ingestion stopped")


async def main():
    """Main entry point for ingestion task."""
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else os.getenv('INGESTION_MODE', 'websocket')
    
    task = DataIngestionTask(ingestion_mode=mode)
    await task.start()


if __name__ == '__main__':
    asyncio.run(main())

