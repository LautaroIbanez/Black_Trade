"""Authentication and onboarding endpoints with KYC/AML integration."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

from backend.auth.permissions import init_auth_service, get_auth_service, Role
from backend.compliance.kyc_aml import get_kyc_service
from backend.repositories.kyc_repository import KYCRepository
from backend.logging.journal import transaction_journal, JournalEntryType
from backend.services.auth_service import app_auth_service


router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    country: str
    role: Role = Role.VIEWER


class VerifyRequest(BaseModel):
    user_id: str
    document_type: Optional[str] = None
    document_number: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    role: Role = Role.VIEWER


class RefreshRequest(BaseModel):
    refresh_token: str


class KYCStatusRequest(BaseModel):
    user_id: str


@router.post("/register")
async def register(req: RegisterRequest) -> Dict[str, Any]:
    auth = get_auth_service() or init_auth_service()
    pair = app_auth_service.issue_tokens(req.username, req.role)
    KYCRepository().upsert(pair.user_id, req.username, req.email, req.country, verified=False)
    kyc = get_kyc_service()
    kyc.register_user(pair.user_id, req.username, req.email, req.country)
    transaction_journal.log(JournalEntryType.SYSTEM_EVENT, details={"event": "register", "user": req.username, "role": req.role.value})
    return {"access_token": pair.access_token, "refresh_token": pair.refresh_token, "user_id": pair.user_id, "role": pair.role}


@router.post("/verify")
async def verify(req: VerifyRequest) -> Dict[str, Any]:
    kyc = get_kyc_service()
    ok = kyc.verify_user(req.user_id, {"document_type": req.document_type, "document_number": req.document_number})
    if not ok:
        raise HTTPException(status_code=404, detail="User not found for KYC")
    KYCRepository().upsert(req.user_id, name=req.user_id, email="", country="", verified=True, verified_at=datetime.utcnow())
    transaction_journal.log(JournalEntryType.SYSTEM_EVENT, details={"event": "kyc_verified", "user_id": req.user_id})
    return {"verified": True}


@router.post("/login")
async def login(req: LoginRequest) -> Dict[str, Any]:
    pair = app_auth_service.issue_tokens(req.username, req.role)
    transaction_journal.log(JournalEntryType.SYSTEM_EVENT, details={"event": "login", "user": req.username, "role": req.role.value})
    return {"access_token": pair.access_token, "refresh_token": pair.refresh_token, "user_id": pair.user_id, "role": pair.role}


@router.post("/refresh")
async def refresh(req: RefreshRequest) -> Dict[str, Any]:
    from backend.services.auth_service import AppAuthService
    from backend.repositories.user_tokens_repository import UserTokensRepository
    from datetime import datetime, timedelta
    import jwt
    repo = UserTokensRepository()
    token_rec = repo.get(req.refresh_token)
    if not token_rec or token_rec.token_type != 'refresh':
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if token_rec.expires_at and datetime.utcnow() > token_rec.expires_at:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    try:
        payload = jwt.decode(req.refresh_token, app_auth_service.secret, algorithms=['HS256'])
        user_id = payload.get('sub')
        username = payload.get('username', user_id)
        new_pair = app_auth_service.issue_tokens(username, Role.VIEWER)
        transaction_journal.log(JournalEntryType.SYSTEM_EVENT, details={"event": "token_refresh", "user_id": user_id})
        return {"access_token": new_pair.access_token, "refresh_token": new_pair.refresh_token, "user_id": new_pair.user_id, "role": new_pair.role}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/kyc-status")
async def kyc_status(req: KYCStatusRequest) -> Dict[str, Any]:
    kyc = get_kyc_service()
    rec = kyc.get_verification_status(req.user_id)
    if not rec:
        return {"verified": False, "status": "not_found"}
    db_verified = KYCRepository().is_verified(req.user_id)
    return {"verified": db_verified, "status": "verified" if db_verified else "pending", "verification_date": rec.verification_date.isoformat() if rec.verification_date else None}


