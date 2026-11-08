"""Personal physiological baseline computed from a user's own sessions."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..models import AnalysisResult, BaselineRecord, User
from ml.features import FEATURE_META

MIN_SESSIONS = 3


def _usable_analyses(db: Session, user: User, limit: int = 12) -> list[AnalysisResult]:
    stmt = (
        select(AnalysisResult)
        .where(AnalysisResult.user_id == user.id)
        .where(AnalysisResult.quality_score >= 40)
        .where(AnalysisResult.predicted_class.is_not(None))
        .order_by(desc(AnalysisResult.created_at))
        .limit(limit)
    )
    return list(db.scalars(stmt))


def _aggregate(analyses: list[AnalysisResult]) -> dict[str, dict[str, float]]:
    collected: dict[str, list[float]] = {}
    for analysis in analyses:
        try:
            features = json.loads(analysis.features or "{}")
        except json.JSONDecodeError:
            continue
        for name, value in features.items():
            if isinstance(value, (int, float)) and np.isfinite(value):
                collected.setdefault(name, []).append(float(value))
    summary = {}
    for name, values in collected.items():
        if len(values) < MIN_SESSIONS:
            continue
        arr = np.asarray(values, dtype=float)
        summary[name] = {
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0, 4),
            "min": round(float(np.min(arr)), 4),
            "max": round(float(np.max(arr)), 4),
            "n": int(arr.size),
            "label": FEATURE_META.get(name, {}).get("label", name),
            "unit": FEATURE_META.get(name, {}).get("unit", ""),
            "group": FEATURE_META.get(name, {}).get("group", ""),
        }
    return summary


def get_active(db: Session, user: User) -> BaselineRecord | None:
    return db.scalars(
        select(BaselineRecord)
        .where(BaselineRecord.user_id == user.id)
        .where(BaselineRecord.is_active.is_(True))
        .order_by(desc(BaselineRecord.created_at))
    ).first()


def baseline_payload(db: Session, user: User) -> dict[str, Any]:
    analyses = _usable_analyses(db, user)
    min_required = max(MIN_SESSIONS, user.profile.baseline_min_sessions if user.profile else 5)
    active = get_active(db, user)

    if not user.profile or not user.profile.allow_baseline:
        return {
            "enabled": False,
            "session_count": len(analyses),
            "required_sessions": min_required,
            "reliable": False,
            "reliability": "disabled",
            "message": "Baseline calculation is turned off in your privacy settings.",
            "features": {},
            "trend": _trend(analyses),
            "disclaimer": BASELINE_DISCLAIMER,
        }

    if active is not None:
        computed = json.loads(active.features or "{}")
        session_count = active.session_count
        updated = active.created_at.isoformat() if active.created_at else None
    else:
        computed = _aggregate(analyses)
        session_count = len(analyses)
        updated = None

    if session_count < min_required:
        reliability = "insufficient"
        message = (
            f"{session_count} of {min_required} sessions collected. "
            "The baseline is not yet reliable; keep completing analyses."
        )
    elif session_count < min_required + 5:
        reliability = "provisional"
        message = (
            f"Baseline from {session_count} sessions. This is provisional and exploratory — "
            "individual physiology changes with sleep, activity, caffeine and illness."
        )
    else:
        reliability = "moderate"
        message = (
            f"Baseline from {session_count} sessions. Treat it as a personal reference range, "
            "not a clinical norm."
        )

    return {
        "enabled": True,
        "session_count": session_count,
        "required_sessions": min_required,
        "reliable": session_count >= min_required,
        "reliability": reliability,
        "message": message,
        "updated_at": updated,
        "version": active.version if active else None,
        "features": computed,
        "trend": _trend(analyses),
        "disclaimer": BASELINE_DISCLAIMER,
    }


def _trend(analyses: list[AnalysisResult]) -> list[dict[str, Any]]:
    trend = []
    for analysis in sorted(analyses, key=lambda a: a.created_at or 0):
        try:
            features = json.loads(analysis.features or "{}")
        except json.JSONDecodeError:
            features = {}
        trend.append(
            {
                "id": analysis.id,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                "stress_probability": analysis.stress_score,
                "hr_mean": features.get("hr_mean"),
                "eda_mean": features.get("eda_mean"),
                "rmssd": features.get("rmssd"),
                "quality": analysis.quality_score,
            }
        )
    return trend


BASELINE_DISCLAIMER = (
    "AuraSense baselines are an exploratory feature. They describe your own recorded signal windows and are not "
    "validated for personalised stress detection. WESAD has not established that baseline adaptation improves "
    "accuracy for every individual, and a baseline does not account for sleep, caffeine, illness or activity."
)


def recalibrate(db: Session, user: User) -> BaselineRecord:
    analyses = _usable_analyses(db, user)
    summary = _aggregate(analyses)
    if len(analyses) < MIN_SESSIONS or not summary:
        raise ValueError(
            f"At least {MIN_SESSIONS} completed analyses with adequate signal quality are required to recalibrate."
        )
    existing = db.scalars(
        select(BaselineRecord).where(BaselineRecord.user_id == user.id)
    ).all()
    version = max([b.version for b in existing], default=0) + 1
    for record in existing:
        record.is_active = False
    baseline = BaselineRecord(
        user_id=user.id,
        features=json.dumps(summary),
        session_count=len(analyses),
        session_ids=json.dumps([a.id for a in analyses]),
        version=version,
        is_active=True,
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def reset(db: Session, user: User) -> int:
    records = db.scalars(
        select(BaselineRecord)
        .where(BaselineRecord.user_id == user.id)
        .where(BaselineRecord.is_active.is_(True))
    ).all()
    for record in records:
        record.is_active = False
    db.commit()
    return len(records)


def compare(analysis: AnalysisResult, baseline_features: dict[str, Any]) -> dict[str, Any]:
    try:
        features = json.loads(analysis.features or "{}")
    except json.JSONDecodeError:
        features = {}
    comparisons = []
    for name, stats in baseline_features.items():
        value = features.get(name)
        if not isinstance(value, (int, float)) or not np.isfinite(value):
            continue
        std = max(float(stats.get("std", 0.0)), 1e-6)
        z = (float(value) - float(stats.get("mean", 0.0))) / std
        comparisons.append(
            {
                "feature": name,
                "label": stats.get("label", name),
                "unit": stats.get("unit", ""),
                "value": round(float(value), 3),
                "baseline_mean": round(float(stats.get("mean", 0.0)), 3),
                "z_score": round(float(z), 2),
                "direction": "above" if z > 0 else "below",
            }
        )
    comparisons.sort(key=lambda item: abs(item["z_score"]), reverse=True)
    notable = [c for c in comparisons if abs(c["z_score"]) >= 1.0][:6]
    return {
        "available": bool(comparisons),
        "comparisons": comparisons[:10],
        "notable": notable,
        "summary": (
            f"{len(notable)} feature(s) differ from your baseline by at least one standard deviation."
            if notable
            else "No feature differs from your baseline by more than one standard deviation."
        ),
    }
