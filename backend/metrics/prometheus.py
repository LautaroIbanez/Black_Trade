"""Prometheus metrics for ingestion monitoring."""
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
ingestion_candles_total = Counter(
    'ingestion_candles_processed_total',
    'Total number of candles processed',
    ['symbol', 'timeframe', 'mode']
)

ingestion_errors_total = Counter(
    'ingestion_errors_total',
    'Total number of ingestion errors',
    ['symbol', 'timeframe', 'error_type']
)

ingestion_latency_seconds = Histogram(
    'ingestion_latency_seconds',
    'Latency from candle timestamp to ingestion',
    ['symbol', 'timeframe'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

ingestion_queue_size = Gauge(
    'ingestion_queue_size',
    'Current size of ingestion queue',
    ['queue_name']
)

ingestion_status = Gauge(
    'ingestion_status',
    'Ingestion status (1=active, 0=inactive/error)',
    ['symbol', 'timeframe', 'mode']
)


def record_candle_processed(symbol: str, timeframe: str, mode: str = 'websocket'):
    """Record a processed candle."""
    ingestion_candles_total.labels(symbol=symbol, timeframe=timeframe, mode=mode).inc()


def record_error(symbol: str, timeframe: str, error_type: str):
    """Record an ingestion error."""
    ingestion_errors_total.labels(symbol=symbol, timeframe=timeframe, error_type=error_type).inc()


def record_latency(symbol: str, timeframe: str, latency_seconds: float):
    """Record ingestion latency."""
    ingestion_latency_seconds.labels(symbol=symbol, timeframe=timeframe).observe(latency_seconds)


def set_queue_size(queue_name: str, size: int):
    """Set queue size metric."""
    ingestion_queue_size.labels(queue_name=queue_name).set(size)


def set_ingestion_status(symbol: str, timeframe: str, mode: str, active: bool):
    """Set ingestion status metric."""
    ingestion_status.labels(symbol=symbol, timeframe=timeframe, mode=mode).set(1 if active else 0)

