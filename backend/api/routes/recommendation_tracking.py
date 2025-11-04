"""Dedicated tracking endpoints for recommendations (accept/reject/outcome)."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.repositories.recommendation_tracking_repository import RecommendationTrackingRepository
from backend.auth.permissions import Permission
from backend.api.dependencies import require_recommendation_access
from backend.repositories.kyc_repository import KYCRepository
from backend.schemas.validators import sanitize_text
from backend.observability.metrics import get_metrics_collector


router = APIRouter(prefix="/api/recommendation-tracking", tags=["recommendations"])
repo = RecommendationTrackingRepository()


class TrackingRequest(BaseModel):
    recommendation_id: Optional[int] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    checklist: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


@router.post("/accept")
async def accept(req: TrackingRequest, user=Depends(require_recommendation_access)):
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    if req.recommendation_id:
        ok = repo.update(req.recommendation_id, status='accepted', checklist=req.checklist, notes=sanitize_text(req.notes or ''))
        if not ok:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        try:
            get_metrics_collector().record_strategy_metric('system', 'recommendation_accepted', 1)
        except Exception:
            pass
        return {"success": True, "id": req.recommendation_id}
    if not (req.symbol and req.timeframe and req.payload):
        raise HTTPException(status_code=400, detail="symbol, timeframe, payload required")
    rec_id = repo.create('accepted', req.symbol, req.timeframe, req.payload, user_id=user.user_id, checklist=req.checklist, notes=sanitize_text(req.notes or ''))
    try:
        get_metrics_collector().record_strategy_metric('system', 'recommendation_accepted', 1)
    except Exception:
        pass
    return {"success": True, "id": rec_id}


@router.post("/reject")
async def reject(req: TrackingRequest, user=Depends(require_recommendation_access)):
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    if req.recommendation_id:
        ok = repo.update(req.recommendation_id, status='rejected', checklist=req.checklist, notes=sanitize_text(req.notes or ''))
        if not ok:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        try:
            get_metrics_collector().record_strategy_metric('system', 'recommendation_rejected', 1)
        except Exception:
            pass
        return {"success": True, "id": req.recommendation_id}
    if not (req.symbol and req.timeframe and req.payload):
        raise HTTPException(status_code=400, detail="symbol, timeframe, payload required")
    rec_id = repo.create('rejected', req.symbol, req.timeframe, req.payload, user_id=user.user_id, checklist=req.checklist, notes=sanitize_text(req.notes or ''))
    try:
        get_metrics_collector().record_strategy_metric('system', 'recommendation_rejected', 1)
    except Exception:
        pass
    return {"success": True, "id": rec_id}


class OutcomeRequest(BaseModel):
    recommendation_id: int
    outcome: str  # win|loss|breakeven
    realized_pnl: Optional[float] = None
    notes: Optional[str] = None


@router.post("/outcome")
async def outcome(req: OutcomeRequest, user=Depends(require_recommendation_access)):
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    ok = repo.update(req.recommendation_id, outcome=req.outcome, realized_pnl=req.realized_pnl, notes=sanitize_text(req.notes or ''))
    if not ok:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    # Metric: record hit
    try:
        mkey = 'recommendation_win' if str(req.outcome).lower() == 'win' else 'recommendation_loss'
        get_metrics_collector().record_strategy_metric('system', mkey, 1)
    except Exception:
        pass
    return {"success": True, "id": req.recommendation_id}


@router.get("/history")
async def history(limit: int = 50, user=Depends(require_recommendation_access)):
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    return {"items": repo.history(limit=limit)}


@router.get("/metrics")
async def metrics(days: int = 30, user=Depends(require_recommendation_access)):
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    return repo.get_metrics(days=days)


