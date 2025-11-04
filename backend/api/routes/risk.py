"""API routes for risk management."""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.risk.engine import RiskEngine, RiskLimits, RiskMetrics
from backend.integrations.base import ExchangeAdapter
from backend.auth.permissions import Permission
from backend.api.dependencies import require_risk_metrics_access, require_write_risk_limits_access
from backend.repositories.kyc_repository import KYCRepository
from backend.config.security import rate_limit

router = APIRouter(tags=["risk"])  # Prefix is added in app.py


class RiskLimitsRequest(BaseModel):
    """Request model for updating risk limits."""
    max_exposure_pct: Optional[float] = None
    max_position_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    daily_loss_limit_pct: Optional[float] = None
    var_limit_1d_95: Optional[float] = None
    var_limit_1w_95: Optional[float] = None


class PositionSizeRequest(BaseModel):
    """Request model for position sizing."""
    entry_price: float
    stop_loss: float
    risk_amount: Optional[float] = None
    strategy_name: Optional[str] = None
    method: str = "risk_based"


# Global risk engine (would be injected via dependency in production)
_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Get or create risk engine instance."""
    global _risk_engine
    if _risk_engine is None:
        raise HTTPException(status_code=503, detail="Risk engine not initialized")
    return _risk_engine


def set_risk_engine(engine: RiskEngine):
    """Set risk engine instance."""
    global _risk_engine
    _risk_engine = engine


@router.get("/status")
@rate_limit(max_requests=120, window_seconds=60)
async def get_risk_status(request: Request, engine: RiskEngine = Depends(get_risk_engine), user=Depends(require_risk_metrics_access)) -> Dict[str, Any]:
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    """Get current risk status."""
    try:
        metrics = engine.get_risk_metrics()
        checks = engine.check_risk_limits(metrics)
        
        return {
            "metrics": {
                "total_capital": metrics.total_capital,
                "equity": metrics.equity,
                "total_exposure": metrics.total_exposure,
                "exposure_pct": metrics.exposure_pct,
                "unrealized_pnl": metrics.unrealized_pnl,
                "daily_pnl": metrics.daily_pnl,
                "current_drawdown_pct": metrics.current_drawdown_pct,
                "max_drawdown_pct": metrics.max_drawdown_pct,
                "peak_equity": metrics.peak_equity,
                "var_1d_95": metrics.var_1d_95,
                "var_1d_99": metrics.var_1d_99,
                "var_1w_95": metrics.var_1w_95,
                "var_1w_99": metrics.var_1w_99,
                "timestamp": metrics.timestamp.isoformat(),
            },
            "limits": {
                "max_exposure_pct": engine.risk_limits.max_exposure_pct,
                "max_position_pct": engine.risk_limits.max_position_pct,
                "max_drawdown_pct": engine.risk_limits.max_drawdown_pct,
                "daily_loss_limit_pct": engine.risk_limits.daily_loss_limit_pct,
                "var_limit_1d_95": engine.risk_limits.var_limit_1d_95,
                "var_limit_1w_95": engine.risk_limits.var_limit_1w_95,
            },
            "limit_checks": checks,
            "status": "healthy" if not any(c["violated"] for c in checks.values()) else "violations",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exposure")
@rate_limit(max_requests=120, window_seconds=60)
async def get_exposure(request: Request, engine: RiskEngine = Depends(get_risk_engine), user=Depends(require_risk_metrics_access)) -> Dict[str, Any]:
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    """Get exposure breakdown by asset and strategy."""
    try:
        exposure_data = engine.calculate_exposure()
        return exposure_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/var")
async def get_var(
    confidence_levels: str = "0.95,0.99",
    horizons: str = "1,7",
    engine: RiskEngine = Depends(get_risk_engine),
) -> Dict[str, Any]:
    """Get Value at Risk calculations."""
    try:
        conf_levels = [float(c) for c in confidence_levels.split(',')]
        horizon_days = [int(h) for h in horizons.split(',')]
        
        var_data = engine.calculate_var(confidence_levels=conf_levels, horizons=horizon_days)
        
        # Get current equity for context
        account_status = engine.adapter.get_account_status()
        
        return {
            "var_values": var_data,
            "equity": account_status.get('equity', 0),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drawdown")
@rate_limit(max_requests=120, window_seconds=60)
async def get_drawdown(request: Request, engine: RiskEngine = Depends(get_risk_engine), user=Depends(require_risk_metrics_access)) -> Dict[str, Any]:
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    """Get drawdown metrics."""
    try:
        drawdown_data = engine.calculate_drawdown()
        metrics = engine.get_risk_metrics()
        
        return {
            **drawdown_data,
            "daily_pnl": metrics.daily_pnl,
            "daily_pnl_pct": (metrics.daily_pnl / metrics.total_capital * 100) if metrics.total_capital > 0 else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limits")
@rate_limit(max_requests=60, window_seconds=60)
async def get_limits(request: Request, engine: RiskEngine = Depends(get_risk_engine), user=Depends(require_risk_metrics_access)) -> Dict[str, Any]:
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    """Get current risk limits."""
    return {
        "global_limits": {
            "max_exposure_pct": engine.risk_limits.max_exposure_pct,
            "max_position_pct": engine.risk_limits.max_position_pct,
            "max_drawdown_pct": engine.risk_limits.max_drawdown_pct,
            "daily_loss_limit_pct": engine.risk_limits.daily_loss_limit_pct,
            "var_limit_1d_95": engine.risk_limits.var_limit_1d_95,
            "var_limit_1w_95": engine.risk_limits.var_limit_1w_95,
        },
        "strategy_limits": engine.strategy_limits,
    }


@router.post("/limits")
@rate_limit(max_requests=30, window_seconds=60)
async def update_limits(
    request: Request,
    limits: RiskLimitsRequest,
    engine: RiskEngine = Depends(get_risk_engine),
    user=Depends(require_write_risk_limits_access),
) -> Dict[str, Any]:
    """Update risk limits."""
    try:
        # Update global limits
        if limits.max_exposure_pct is not None:
            engine.risk_limits.max_exposure_pct = limits.max_exposure_pct
        if limits.max_position_pct is not None:
            engine.risk_limits.max_position_pct = limits.max_position_pct
        if limits.max_drawdown_pct is not None:
            engine.risk_limits.max_drawdown_pct = limits.max_drawdown_pct
        if limits.daily_loss_limit_pct is not None:
            engine.risk_limits.daily_loss_limit_pct = limits.daily_loss_limit_pct
        if limits.var_limit_1d_95 is not None:
            engine.risk_limits.var_limit_1d_95 = limits.var_limit_1d_95
        if limits.var_limit_1w_95 is not None:
            engine.risk_limits.var_limit_1w_95 = limits.var_limit_1w_95
        
        # Broadcast change via WebSocket
        try:
            from backend.api.routes.websocket import manager
            import asyncio
            async def _broadcast():
                await manager.broadcast({
                    "type": "risk_limits_changed",
                    "payload": {
                        "limits": {
                            "max_exposure_pct": engine.risk_limits.max_exposure_pct,
                            "max_position_pct": engine.risk_limits.max_position_pct,
                            "max_drawdown_pct": engine.risk_limits.max_drawdown_pct,
                            "daily_loss_limit_pct": engine.risk_limits.daily_loss_limit_pct,
                            "var_limit_1d_95": engine.risk_limits.var_limit_1d_95,
                            "var_limit_1w_95": engine.risk_limits.var_limit_1w_95,
                        }
                    }
                })
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_broadcast())
            else:
                loop.run_until_complete(_broadcast())
        except Exception:
            pass

        return {
            "message": "Limits updated successfully",
            "limits": {
                "max_exposure_pct": engine.risk_limits.max_exposure_pct,
                "max_position_pct": engine.risk_limits.max_position_pct,
                "max_drawdown_pct": engine.risk_limits.max_drawdown_pct,
                "daily_loss_limit_pct": engine.risk_limits.daily_loss_limit_pct,
                "var_limit_1d_95": engine.risk_limits.var_limit_1d_95,
                "var_limit_1w_95": engine.risk_limits.var_limit_1w_95,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/position-size")
async def calculate_position_size(
    request: PositionSizeRequest,
    engine: RiskEngine = Depends(get_risk_engine),
) -> Dict[str, Any]:
    """Calculate recommended position size."""
    try:
        # Get risk amount if not provided
        risk_amount = request.risk_amount
        if risk_amount is None:
            account_status = engine.adapter.get_account_status()
            equity = account_status.get('equity', 0)
            # Default: risk 1% of equity
            risk_amount = equity * 0.01
        
        sizing = engine.calculate_position_size(
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            risk_amount=risk_amount,
            strategy_name=request.strategy_name,
            method=request.method,
        )
        
        return sizing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions(engine: RiskEngine = Depends(get_risk_engine)) -> Dict[str, Any]:
    """Get current positions with risk metrics."""
    try:
        positions = engine.adapter.get_positions()
        exposure_data = engine.calculate_exposure(positions)
        
        return {
            "positions": positions,
            "exposure_summary": {
                "total_exposure": exposure_data['total_exposure'],
                "exposure_pct": exposure_data['exposure_pct'],
                "exposure_by_asset": exposure_data['exposure_by_asset'],
                "exposure_by_strategy": exposure_data['exposure_by_strategy'],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

