"""API routes for observability metrics and health checks."""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime

from backend.observability.metrics import get_metrics_collector
from backend.observability.telemetry import get_telemetry_manager

router = APIRouter(tags=["observability"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "black-trade",
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    collector = get_metrics_collector()
    metrics = collector.get_metrics()
    
    return {
        "timestamp": metrics.timestamp.isoformat(),
        "latency": {
            "p50_ms": metrics.api_latency_p50,
            "p95_ms": metrics.api_latency_p95,
            "p99_ms": metrics.api_latency_p99,
        },
        "throughput": {
            "requests_per_second": metrics.requests_per_second,
            "orders_per_minute": metrics.orders_per_minute,
        },
        "errors": {
            "error_rate_percent": metrics.error_rate,
            "order_rejection_rate_percent": metrics.order_rejection_rate,
        },
        "performance": {
            "recommendation_generation_time_ms": metrics.recommendation_generation_time,
            "order_execution_time_ms": metrics.order_execution_time,
        },
        "system": {
            "memory_usage_mb": metrics.memory_usage_mb,
            "cpu_usage_percent": metrics.cpu_usage_percent,
        },
        "trading": {
            "total_pnl": metrics.total_pnl,
            "daily_pnl": metrics.daily_pnl,
            "win_rate": metrics.win_rate,
            "sharpe_ratio": metrics.sharpe_ratio,
        },
        "risk": {
            "current_drawdown": metrics.current_drawdown,
            "max_drawdown": metrics.max_drawdown,
            "exposure_percent": metrics.exposure_percent,
            "var_1d_95": metrics.var_1d_95,
        },
        "strategy_performance": metrics.strategy_performance,
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with component status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {},
    }
    
    # Check telemetry
    telemetry_manager = get_telemetry_manager()
    health_status["components"]["telemetry"] = {
        "status": "ok" if telemetry_manager.initialized else "disabled",
        "tracing_enabled": telemetry_manager.enable_tracing,
        "metrics_enabled": telemetry_manager.enable_metrics,
    }
    
    # Check metrics collector
    metrics_collector = get_metrics_collector()
    metrics = metrics_collector.get_metrics()
    health_status["components"]["metrics"] = {
        "status": "ok",
        "total_requests": metrics_collector.total_requests,
        "error_rate": metrics.error_rate,
    }
    
    # Determine overall status
    if metrics.error_rate > 10.0:  # More than 10% error rate
        health_status["status"] = "degraded"
    
    return health_status

