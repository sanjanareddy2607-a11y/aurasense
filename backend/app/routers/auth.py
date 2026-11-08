"""Authentication, account and privacy endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import (
    AnalysisResult,
    BaselineRecord,
    Dataset,
    MonitoringSession,
    Profile,
    Report,
    SignalAsset,
    User,
)
from ..schemas import (
    AccountDeleteIn,
    LoginIn,
    PasswordChangeIn,
    ProfileUpdateIn,
    RegisterIn,
)
from ..security import create_access_token, hash_password, verify_password
from ..services.serializers import user_dict

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
        "user": user_dict(user),
    }


@router.post("/register", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> dict:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    role = "individual"
    if payload.role == "researcher":
        if (payload.institution_code or "").strip() != settings.research_invite_code:
            raise HTTPException(
                status_code=403,
                detail="A valid institutional research code is required for researcher accounts.",
            )
        role = "researcher"

    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=role,
    )
    user.profile = Profile(display_name=payload.name.strip(), share_aggregate=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="This account has been deactivated.")
    return _token_response(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_dict(user)


@router.patch("/profile")
def update_profile(
    payload: ProfileUpdateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    profile = user.profile or Profile(user_id=user.id)
    if user.profile is None:
        db.add(profile)
    if payload.name is not None:
        user.name = payload.name.strip()
    for field in (
        "display_name",
        "organisation",
        "share_aggregate",
        "store_raw_signals",
        "allow_baseline",
        "baseline_min_sessions",
        "data_note",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value)
    db.commit()
    db.refresh(user)
    return user_dict(user)


@router.post("/password")
def change_password(
    payload: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True, "message": "Password updated."}


@router.delete("/account")
def delete_account(
    payload: AccountDeleteIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect.")
    if user.is_demo:
        raise HTTPException(
            status_code=403,
            detail="Shared demonstration accounts cannot be deleted. Create your own account to manage data.",
        )
    for model in (AnalysisResult, MonitoringSession, SignalAsset, BaselineRecord, Report):
        for row in db.scalars(select(model).where(model.user_id == user.id)).all():
            db.delete(row)
    for dataset in db.scalars(select(Dataset).where(Dataset.uploaded_by == user.id)).all():
        dataset.uploaded_by = None
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "Account and associated records deleted."}


@router.get("/export")
def export_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.scalars(
        select(AnalysisResult).where(AnalysisResult.user_id == user.id).order_by(AnalysisResult.created_at)
    ).all()
    sessions = db.scalars(select(MonitoringSession).where(MonitoringSession.user_id == user.id)).all()
    baselines = db.scalars(select(BaselineRecord).where(BaselineRecord.user_id == user.id)).all()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "product": "AuraSense",
        "notice": "AuraSense estimates physiological pattern similarity. This is not a medical record.",
        "account": {
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "profile": user_dict(user)["profile"],
        },
        "sessions": [
            {
                "id": s.id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "scenario": s.scenario,
                "status": s.status,
                "data_source": s.data_source,
                "is_simulation": s.is_simulation,
                "duration_seconds": s.duration_seconds,
                "quality_grade": s.quality_grade,
            }
            for s in sessions
        ],
        "analyses": [
            {
                "id": a.id,
                "title": a.title,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "source_type": a.source_type,
                "source_label": a.source_label,
                "predicted_class": a.predicted_class,
                "predicted_label": a.predicted_label,
                "confidence": a.confidence,
                "stress_probability": a.stress_score,
                "quality_score": a.quality_score,
                "is_demo": a.is_demo,
                "features": json.loads(a.features or "{}"),
                "imputed_features": json.loads(a.imputed_features or "[]"),
            }
            for a in analyses
        ],
        "baselines": [
            {
                "version": b.version,
                "session_count": b.session_count,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "is_active": b.is_active,
                "features": json.loads(b.features or "{}"),
            }
            for b in baselines
        ],
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="aurasense-export.json"'},
    )
