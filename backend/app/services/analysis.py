"""Analysis orchestration: signals -> quality -> features -> inference -> DB."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from ..models import AnalysisResult, Dataset, User
from ml.features import FEATURE_META, extract_window_features, features_from_frame
from . import inference


def _persist(
    db: Session,
    *,
    user: User,
    result: dict[str, Any],
    windows: list[dict[str, Any]],
    title: str,
    source_type: str,
    source_label: str,
    session_id: str | None = None,
    dataset_id: str | None = None,
    duration: float = 0.0,
    is_demo: bool = False,
    notes: str | None = None,
) -> AnalysisResult:
    explanation = result.get("explanation", {})
    record = AnalysisResult(
        user_id=user.id,
        session_id=session_id,
        dataset_id=dataset_id,
        title=title,
        source_type=source_type,
        source_label=source_label,
        model_version=result.get("model_version") or "unavailable",
        predicted_class=result.get("predicted_class"),
        predicted_label=result.get("predicted_label") or "Insufficient signal quality",
        confidence=result.get("confidence"),
        uncertainty=result.get("uncertainty"),
        stress_score=result.get("stress_probability"),
        class_probabilities=json.dumps(result.get("class_probabilities", {})),
        quality_score=result.get("quality", {}).get("score"),
        quality_grade=result.get("quality", {}).get("grade"),
        quality_issues=json.dumps(result.get("quality", {}).get("issues", [])),
        features=json.dumps(result.get("features", {})),
        imputed_features=json.dumps(result.get("imputed_features", [])),
        explanation=json.dumps(explanation),
        window_count=len(windows),
        duration_seconds=float(duration),
        notes=notes,
        is_demo=is_demo,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def analyse_dataframe(
    db: Session,
    user: User,
    df,
    *,
    title: str,
    source_type: str,
    source_label: str,
    fs_hint: float | None = None,
    dataset_id: str | None = None,
    is_demo: bool = False,
) -> tuple[AnalysisResult, dict[str, Any]]:
    parsed = features_from_frame(df, fs_hint=fs_hint)
    result = inference.predict_windows(parsed["windows"])
    record = _persist(
        db,
        user=user,
        result=result,
        windows=parsed["windows"],
        title=title,
        source_type=source_type,
        source_label=source_label,
        dataset_id=dataset_id,
        duration=parsed["duration_seconds"],
        is_demo=is_demo,
    )
    return record, parsed


def analyse_channels(
    db: Session,
    user: User,
    channels: dict[str, Any],
    fs: float | dict[str, float],
    *,
    title: str,
    source_type: str,
    source_label: str,
    duration: float,
    session_id: str | None = None,
    is_demo: bool = False,
) -> tuple[AnalysisResult, dict[str, Any]]:
    from ml.features import assess_quality

    features = extract_window_features(channels, fs, duration)
    quality = assess_quality(channels, fs, duration)
    window = {"features": features, "quality": quality}
    result = inference.predict_windows([window])
    record = _persist(
        db,
        user=user,
        result=result,
        windows=[window],
        title=title,
        source_type=source_type,
        source_label=source_label,
        session_id=session_id,
        duration=duration,
        is_demo=is_demo,
    )
    return record, {"features": features, "quality": quality, "result": result}


def analyse_reference_window(
    db: Session, user: User, subject: str | None, label: str | None
) -> tuple[AnalysisResult, dict[str, Any]]:
    """Inference on a cached WESAD window (features extracted offline)."""
    features_path = inference.ARTIFACTS / "wesad_features.csv"
    if not features_path.exists():
        raise FileNotFoundError("WESAD feature cache is not available. Run `python -m ml.wesad_extract`.")
    import pandas as pd

    frame = pd.read_csv(features_path)
    if subject:
        frame = frame[frame["subject"] == subject]
    if label:
        frame = frame[frame["label"] == label]
    if frame.empty:
        raise ValueError("No cached WESAD window matches that selection.")
    row = frame.sample(1, random_state=None).iloc[0]
    from ml.features import FEATURE_NAMES

    features = {
        name: (float(row[name]) if name in row and np.isfinite(row[name]) else float("nan"))
        for name in FEATURE_NAMES
    }
    window = {
        "features": features,
        "quality": {
            "score": float(row.get("quality_score", 80)),
            "grade": str(row.get("quality_grade", "good")),
            "issues": [],
        },
    }
    result = inference.predict_windows([window])
    record = _persist(
        db,
        user=user,
        result=result,
        windows=[window],
        title=f"WESAD reference window — {row['subject']} / {row['label']}",
        source_type="wesad_reference",
        source_label=f"WESAD {row['subject']} {row['label']} window "
        f"{row['start_seconds']:.0f}–{row['end_seconds']:.0f}s (cached offline features)",
        duration=float(row["end_seconds"] - row["start_seconds"]),
    )
    meta = {
        "subject": row["subject"],
        "label": row["label"],
        "start_seconds": float(row["start_seconds"]),
        "end_seconds": float(row["end_seconds"]),
        "features": features,
        "quality": window["quality"],
        "result": result,
        "feature_labels": {k: v["label"] for k, v in FEATURE_META.items()},
    }
    return record, meta


def demo_dataset(db: Session, dataset_id: str) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found.")
    return dataset
