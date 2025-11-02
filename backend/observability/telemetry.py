"""OpenTelemetry instrumentation for distributed tracing and metrics."""
import logging
import os
from typing import Optional, Dict, Any
from functools import wraps
import time

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manager for OpenTelemetry instrumentation."""
    
    def __init__(
        self,
        service_name: str = "black-trade",
        otlp_endpoint: Optional[str] = None,
        enable_tracing: bool = True,
        enable_metrics: bool = True,
    ):
        """
        Initialize telemetry manager.
        
        Args:
            service_name: Service name for telemetry
            otlp_endpoint: OTLP endpoint (e.g., "http://localhost:4317")
            enable_tracing: Enable distributed tracing
            enable_metrics: Enable metrics collection
        """
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
        self.enable_tracing = enable_tracing
        self.enable_metrics = enable_metrics
        self.initialized = False
        
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk")
            return
        
        if enable_tracing or enable_metrics:
            self._initialize()
    
    def _initialize(self):
        """Initialize OpenTelemetry SDK."""
        if not OPENTELEMETRY_AVAILABLE:
            return
        
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            })
            
            # Initialize tracing
            if self.enable_tracing:
                trace.set_tracer_provider(TracerProvider(resource=resource))
                tracer_provider = trace.get_tracer_provider()
                
                # Add OTLP exporter
                otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
                span_processor = BatchSpanProcessor(otlp_exporter)
                tracer_provider.add_span_processor(span_processor)
                
                logger.info(f"Tracing initialized with OTLP endpoint: {self.otlp_endpoint}")
            
            # Initialize metrics
            if self.enable_metrics:
                metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
                metric_reader = PeriodicExportingMetricReader(
                    metric_exporter,
                    export_interval_millis=60000,  # Export every minute
                )
                metrics.set_meter_provider(MeterProvider(
                    resource=resource,
                    metric_readers=[metric_reader],
                ))
                
                logger.info(f"Metrics initialized with OTLP endpoint: {self.otlp_endpoint}")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")
            self.initialized = False
    
    def get_tracer(self, name: str):
        """Get tracer instance."""
        if not self.enable_tracing or not OPENTELEMETRY_AVAILABLE:
            return None
        
        return trace.get_tracer(name)
    
    def get_meter(self, name: str):
        """Get meter instance."""
        if not self.enable_metrics or not OPENTELEMETRY_AVAILABLE:
            return None
        
        return metrics.get_meter(name)
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI application."""
        if not OPENTELEMETRY_AVAILABLE:
            return
        
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumented with OpenTelemetry")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
    
    def instrument_requests(self):
        """Instrument requests library."""
        if not OPENTELEMETRY_AVAILABLE:
            return
        
        try:
            RequestsInstrumentor().instrument()
            logger.info("Requests library instrumented with OpenTelemetry")
        except Exception as e:
            logger.error(f"Failed to instrument requests: {e}")
    
    def instrument_sqlalchemy(self):
        """Instrument SQLAlchemy."""
        if not OPENTELEMETRY_AVAILABLE:
            return
        
        try:
            SQLAlchemyInstrumentor().instrument()
            logger.info("SQLAlchemy instrumented with OpenTelemetry")
        except Exception as e:
            logger.error(f"Failed to instrument SQLAlchemy: {e}")


def trace_function(tracer_name: str = "default", operation_name: Optional[str] = None):
    """Decorator to trace function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not OPENTELEMETRY_AVAILABLE:
                return func(*args, **kwargs)
            
            from opentelemetry import trace
            tracer = trace.get_tracer(tracer_name)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_async_function(tracer_name: str = "default", operation_name: Optional[str] = None):
    """Decorator to trace async function execution."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not OPENTELEMETRY_AVAILABLE:
                return await func(*args, **kwargs)
            
            from opentelemetry import trace
            tracer = trace.get_tracer(tracer_name)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


# Global telemetry manager instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager() -> TelemetryManager:
    """Get global telemetry manager instance."""
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager


def init_telemetry(
    service_name: str = "black-trade",
    otlp_endpoint: Optional[str] = None,
    enable_tracing: bool = True,
    enable_metrics: bool = True,
) -> TelemetryManager:
    """Initialize global telemetry manager."""
    global _telemetry_manager
    _telemetry_manager = TelemetryManager(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        enable_tracing=enable_tracing,
        enable_metrics=enable_metrics,
    )
    return _telemetry_manager

