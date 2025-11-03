"""API for human-oriented live recommendations and feedback tracking."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from recommendation.engine.prioritizer import RecommendationPrioritizer
from backend.repositories.recommendations_repository import RecommendationsRepository
from backend.auth.permissions import AuthService, Permission
from backend.repositories.kyc_repository import KYCRepository
from backend.observability.metrics import get_metrics_collector
from backend.observability.alerts import ObservabilityAlertManager, AlertType, AlertSeverity


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

prioritizer = RecommendationPrioritizer()
repo = RecommendationsRepository()


class FeedbackRequest(BaseModel):
    status: str  # accepted|rejected
    recommendation_id: Optional[int] = None
    checklist: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


@router.get("/live")
async def get_live_recommendations(profile: str = "balanced", user=Depends(lambda: AuthService().require_permission(Permission.READ_RECOMMENDATIONS))) -> Dict[str, Any]:
    # Enforce KYC verification
    if not KYCRepository().is_verified(user.user_id):
        raise HTTPException(status_code=403, detail="KYC verification required")
    items = prioritizer.generate_live_list(profile=profile)
    # Alert if no items produced
    if not items:
        try:
            ObservabilityAlertManager()._process_alert(
                ObservabilityAlertManager()._create_alert(
                    AlertType.SERVICE_DOWN,
                    AlertSeverity.WARNING,
                    "No live recommendations",
                    "No items produced by prioritizer",
                    {"profile": profile}
                )
            )
        except Exception:
            pass
    return {"items": items, "count": len(items)}


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest) -> Dict[str, Any]:
    if req.recommendation_id:
        updated = repo.update_status(req.recommendation_id, req.status, checklist=req.checklist or {}, notes=req.notes, outcome=req.payload.get('outcome') if req.payload else None, realized_pnl=req.payload.get('realized_pnl') if req.payload else None)
        if not updated:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        try:
            get_metrics_collector().record_strategy_metric('system', 'recommendation_accepted' if req.status=='accepted' else 'recommendation_rejected', 1)
        except Exception:
            pass
        return {"success": True, "id": req.recommendation_id}
    else:
        if not req.payload:
            raise HTTPException(status_code=400, detail="payload required when no recommendation_id")
        symbol = req.payload.get('symbol', 'BTCUSDT')
        timeframe = (req.payload.get('timeframes') or ['1h'])[0]
        rec_id = repo.create(
            status=req.status,
            symbol=symbol,
            timeframe=timeframe,
            confidence=str(req.payload.get('confidence', '')),
            risk_level=str(req.payload.get('risk_level', '')),
            payload=req.payload,
            checklist=req.checklist or {},
            user_id=req.user_id,
            notes=req.notes,
        )
        try:
            get_metrics_collector().record_strategy_metric('system', 'recommendation_accepted' if req.status=='accepted' else 'recommendation_rejected', 1)
        except Exception:
            pass
        return {"success": True, "id": rec_id}


@router.get("/history")
async def list_feedback(limit: int = 20) -> Dict[str, Any]:
    items = repo.list_recent(limit=limit)
    return {"items": items, "count": len(items)}


