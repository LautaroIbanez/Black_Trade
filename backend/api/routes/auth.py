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


@router.post("/register")
async def register(req: RegisterRequest) -> Dict[str, Any]:
    # Create auth user token (not verified yet)
    auth = get_auth_service() or init_auth_service()
    pair = app_auth_service.issue_tokens(req.username, req.role)
    # Create pending KYC in DB
    KYCRepository().upsert(pair.user_id, req.username, req.email, req.country, verified=False)
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


