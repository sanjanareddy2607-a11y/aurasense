"""Personal baseline endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import AnalysisResult, User
from ..services import baseline as baseline_service
from ..services.serializers import baseline_dict, user_dict

router = APIRouter(prefix="/api/baseline", tags=["baseline"])


@router.get("")
def get_baseline(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    payload = baseline_service.baseline_payload(db, user)
    active = baseline_service.get_active(db, user)
    latest_analysis = db.scalars(
        select(AnalysisResult)
        .where(AnalysisResult.user_id == user.id)
        .order_by(desc(AnalysisResult.created_at))
        .limit(1)
    ).first()
    comparison = None
    if latest_analysis and payload.get("features"):
        comparison = baseline_service.compare(latest_analysis, payload["features"])
        comparison["analysis_id"] = latest_analysis.id
        comparison["analysis_title"] = latest_analysis.title
    latest = db.scalars(
        select(AnalysisResult)
        .where(AnalysisResult.user_id == user.id)
        .order_by(desc(AnalysisResult.created_at))
        .limit(10)
    ).all()
    return {
        "baseline": baseline_dict(active, payload),
        "latest_comparison": comparison,
        "eligible_analyses": len([a for a in latest if a.predicted_class]),
        "notice": (
            "Baselines are computed from your own completed analyses. They are exploratory and not clinically "
            "validated; individual physiology varies with sleep, caffeine, activity and illness."
        ),
    }


@router.post("/recalibrate")
def recalibrate(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        record = baseline_service.recalibrate(db, user)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    payload = baseline_service.baseline_payload(db, user)
    return {
        "baseline": baseline_dict(record, payload),
        "notice": "Baseline recalculated from your most recent completed analyses (maximum 12).",
    }


@router.post("/reset")
def reset(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    count = baseline_service.reset(db, user)
    return {
        "ok": True,
        "deactivated": count,
        "message": "Baseline reset. Your analyses are unchanged; a new baseline can be computed later.",
    }
