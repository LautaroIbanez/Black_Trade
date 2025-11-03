"""Metrics collection for KPIs and system health."""
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

try:
    from opentelemetry import metrics
    from opentelemetry.metrics import Counter, Histogram, Gauge
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    # Latency metrics
    api_latency_p50: float = 0.0
    api_latency_p95: float = 0.0
    api_latency_p99: float = 0.0
    
    # Throughput metrics
    requests_per_second: float = 0.0
    orders_per_minute: float = 0.0
    
    # Error rates
    error_rate: float = 0.0
    order_rejection_rate: float = 0.0
    
    # Performance
    recommendation_generation_time: float = 0.0
    order_execution_time: float = 0.0
    
    # System health
    database_connection_pool_size: int = 0
    database_connection_active: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Trading metrics
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Risk metrics
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    exposure_percent: float = 0.0
    var_1d_95: float = 0.0
    
    # Strategy health
    strategy_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """Collector for system metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.meter = None
        if OPENTELEMETRY_AVAILABLE:
            try:
                self.meter = metrics.get_meter("black-trade")
            except Exception as e:
                logger.warning(f"Failed to get OpenTelemetry meter: {e}")
        
        # Internal metrics storage
        self.api_latencies: deque = deque(maxlen=1000)
        self.request_timestamps: deque = deque(maxlen=10000)
        self.error_count = 0
        self.total_requests = 0
        self.order_timestamps: deque = deque(maxlen=1000)
        self.rejected_orders = 0
        self.total_orders = 0
        
        # Strategy metrics
        self.strategy_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'generation_count': 0,
            'generation_times': deque(maxlen=100),
            'order_count': 0,
            'pnl': 0.0,
        })
        
        # Recommendation tracking metrics
        self.recommendation_metrics: Dict[str, int] = defaultdict(int)
        
        # Register OpenTelemetry metrics
        if self.meter:
            self._register_ot_metrics()
    
    def _register_ot_metrics(self):
        """Register OpenTelemetry metrics."""
        try:
            # API latency histogram
            self.api_latency_histogram = self.meter.create_histogram(
                "api_latency_ms",
                description="API request latency in milliseconds",
                unit="ms",
            )
            
            # Request counter
            self.request_counter = self.meter.create_counter(
                "api_requests_total",
                description="Total number of API requests",
            )
            
            # Error counter
            self.error_counter = self.meter.create_counter(
                "api_errors_total",
                description="Total number of API errors",
            )
            
            # Order counter
            self.order_counter = self.meter.create_counter(
                "orders_total",
                description="Total number of orders",
            )
            
            # PnL gauge
            self.pnl_gauge = self.meter.create_up_down_counter(
                "pnl_total",
                description="Total profit and loss",
                unit="USD",
            )
            
            # Drawdown gauge
            self.drawdown_gauge = self.meter.create_up_down_counter(
                "drawdown_percent",
                description="Current drawdown percentage",
                unit="percent",
            )
            
            logger.info("OpenTelemetry metrics registered")
        except Exception as e:
            logger.error(f"Failed to register OpenTelemetry metrics: {e}")
    
    def record_api_request(self, latency_ms: float, status_code: int):
        """Record API request metrics."""
        self.api_latencies.append(latency_ms)
        self.request_timestamps.append(time.time())
        self.total_requests += 1
        
        if status_code >= 400:
            self.error_count += 1
        
        if self.meter:
            try:
                self.api_latency_histogram.record(latency_ms)
                self.request_counter.add(1, {"status_code": str(status_code)})
                if status_code >= 400:
                    self.error_counter.add(1, {"status_code": str(status_code)})
            except Exception as e:
                logger.debug(f"Failed to record OT metric: {e}")
    
    def record_order(self, rejected: bool = False):
        """Record order metrics."""
        self.order_timestamps.append(time.time())
        self.total_orders += 1
        if rejected:
            self.rejected_orders += 1
        
        if self.meter:
            try:
                self.order_counter.add(1, {"rejected": str(rejected)})
            except Exception as e:
                logger.debug(f"Failed to record OT metric: {e}")
    
    def record_strategy_metric(self, strategy_name: str, metric_type: str, value: float):
        """Record strategy-specific metric."""
        if metric_type == 'generation_time':
            self.strategy_metrics[strategy_name]['generation_times'].append(value)
            self.strategy_metrics[strategy_name]['generation_count'] += 1
        elif metric_type == 'pnl':
            self.strategy_metrics[strategy_name]['pnl'] += value
        else:
            # Handle custom metrics like recommendation_accepted, recommendation_win, etc.
            metric_key = f"{strategy_name}_{metric_type}"
            self.recommendation_metrics[metric_key] += int(value)
    
    def calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        now = time.time()
        
        # Calculate latency percentiles
        latencies = list(self.api_latencies) if self.api_latencies else [0]
        latency_p50 = self.calculate_percentile(latencies, 50)
        latency_p95 = self.calculate_percentile(latencies, 95)
        latency_p99 = self.calculate_percentile(latencies, 99)
        
        # Calculate throughput (requests per second)
        if len(self.request_timestamps) > 1:
            time_span = self.request_timestamps[-1] - self.request_timestamps[0]
            requests_per_second = len(self.request_timestamps) / time_span if time_span > 0 else 0
        else:
            requests_per_second = 0.0
        
        # Calculate orders per minute
        recent_orders = [ts for ts in self.order_timestamps if now - ts < 60]
        orders_per_minute = len(recent_orders)
        
        # Calculate error rate
        error_rate = (self.error_count / self.total_requests * 100) if self.total_requests > 0 else 0.0
        
        # Calculate order rejection rate
        order_rejection_rate = (self.rejected_orders / self.total_orders * 100) if self.total_orders > 0 else 0.0
        
        # Calculate strategy performance
        strategy_performance = {}
        for strategy_name, metrics_data in self.strategy_metrics.items():
            if metrics_data['generation_times']:
                avg_generation_time = sum(metrics_data['generation_times']) / len(metrics_data['generation_times'])
            else:
                avg_generation_time = 0.0
            
            strategy_performance[strategy_name] = {
                'generation_count': metrics_data['generation_count'],
                'avg_generation_time_ms': avg_generation_time,
                'order_count': metrics_data['order_count'],
                'pnl': metrics_data['pnl'],
            }
        
        # Get system resources (would integrate with psutil in production)
        try:
            import psutil
            process = psutil.Process()
            memory_usage_mb = process.memory_info().rss / 1024 / 1024
            cpu_usage_percent = process.cpu_percent(interval=0.1)
        except ImportError:
            memory_usage_mb = 0.0
            cpu_usage_percent = 0.0
        
        return SystemMetrics(
            api_latency_p50=latency_p50,
            api_latency_p95=latency_p95,
            api_latency_p99=latency_p99,
            requests_per_second=requests_per_second,
            orders_per_minute=orders_per_minute,
            error_rate=error_rate,
            order_rejection_rate=order_rejection_rate,
            strategy_performance=strategy_performance,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            timestamp=datetime.now(),
        )
    
    def get_recommendation_metrics(self) -> Dict[str, int]:
        """Get recommendation tracking metrics."""
        return dict(self.recommendation_metrics)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

