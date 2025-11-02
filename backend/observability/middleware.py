"""Middleware for observability (logging, metrics, tracing)."""
import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.observability.metrics import get_metrics_collector
from backend.observability.telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for logging, metrics, and tracing."""
    
    def __init__(self, app: ASGIApp):
        """Initialize middleware."""
        super().__init__(app)
        self.metrics_collector = get_metrics_collector()
        self.telemetry_manager = get_telemetry_manager()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with observability."""
        start_time = time.time()
        
        # Get tracer for distributed tracing
        tracer = None
        if self.telemetry_manager.initialized:
            tracer = self.telemetry_manager.get_tracer("api")
        
        # Start span
        span = None
        if tracer:
            span = tracer.start_span(f"{request.method} {request.url.path}")
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.metrics_collector.record_api_request(
                latency_ms=latency_ms,
                status_code=response.status_code,
            )
            
            # Update span
            if span:
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.latency_ms", latency_ms)
            
            # Log request (only if not health check)
            if "/health" not in str(request.url.path):
                logger.info(
                    f"{request.method} {request.url.path} - "
                    f"{response.status_code} - {latency_ms:.2f}ms"
                )
            
            return response
        
        except Exception as e:
            # Record error
            latency_ms = (time.time() - start_time) * 1000
            self.metrics_collector.record_api_request(
                latency_ms=latency_ms,
                status_code=500,
            )
            
            # Update span
            if span:
                from opentelemetry import trace
                span.set_attribute("http.status_code", 500)
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            logger.error(f"Request error: {request.method} {request.url.path} - {e}")
            raise
        
        finally:
            # End span
            if span:
                span.end()

