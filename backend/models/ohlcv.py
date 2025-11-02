"""SQLAlchemy models for OHLCV data."""
from sqlalchemy import Column, BigInteger, String, Numeric, Integer, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func
from datetime import datetime

from backend.models.base import Base


class OHLCVCandle(Base):
    """Model for OHLCV candle data."""
    __tablename__ = 'ohlcv_candles'
    
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(BigInteger, nullable=False, index=True)  # Unix timestamp in ms
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(Numeric(30, 8), nullable=False)
    quote_volume = Column(Numeric(30, 8))
    trades = Column(Integer)
    taker_buy_base = Column(Numeric(30, 8))
    taker_buy_quote = Column(Numeric(30, 8))
    close_time = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uq_ohlcv_symbol_timeframe_timestamp'),
        Index('idx_ohlcv_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=False),
        Index('idx_ohlcv_timestamp', 'timestamp', unique=False),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timestamp': int(self.timestamp),
            'datetime': datetime.fromtimestamp(self.timestamp / 1000).isoformat() if self.timestamp else None,
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': float(self.volume),
            'quote_volume': float(self.quote_volume) if self.quote_volume else None,
            'trades': int(self.trades) if self.trades else None,
            'taker_buy_base': float(self.taker_buy_base) if self.taker_buy_base else None,
            'taker_buy_quote': float(self.taker_buy_quote) if self.taker_buy_quote else None,
            'close_time': int(self.close_time) if self.close_time else None,
        }


class IngestionStatus(Base):
    """Model for tracking ingestion status per symbol/timeframe."""
    __tablename__ = 'ingestion_status'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    last_ingested_timestamp = Column(BigInteger)
    last_ingested_at = Column(DateTime(timezone=True))
    ingestion_mode = Column(String(20))  # 'websocket', 'polling', 'backfill'
    status = Column(String(20), default='active')  # 'active', 'paused', 'error'
    error_message = Column(String)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', name='uq_ingestion_status_symbol_timeframe'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'last_ingested_timestamp': int(self.last_ingested_timestamp) if self.last_ingested_timestamp else None,
            'last_ingested_at': self.last_ingested_at.isoformat() if self.last_ingested_at else None,
            'ingestion_mode': self.ingestion_mode,
            'status': self.status,
            'error_message': self.error_message,
            'latency_ms': int(self.latency_ms) if self.latency_ms else None,
        }


class IngestionMetric(Base):
    """Model for ingestion metrics."""
    __tablename__ = 'ingestion_metrics'
    
    id = Column(BigInteger, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    metric_type = Column(String(50), nullable=False)  # 'latency', 'error_rate', 'throughput'
    metric_value = Column(Numeric(20, 4))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    __table_args__ = (
        Index('idx_metrics_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp', unique=False),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'metric_type': self.metric_type,
            'metric_value': float(self.metric_value) if self.metric_value else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

