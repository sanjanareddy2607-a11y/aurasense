"""Dictionary serialisers shared by routers."""
from __future__ import annotations

import json
from typing import Any

from ..models import (
    AnalysisResult,
    BaselineRecord,
    Dataset,
    MonitoringSession,
    Profile,
    Report,
    ResearchExperiment,
    User,
)


def _json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def iso(value) -> str | None:
    return value.isoformat() if value else None


def user_dict(user: User, profile: Profile | None = None) -> dict[str, Any]:
    profile = profile or user.profile
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "is_demo": user.is_demo,
        "created_at": iso(user.created_at),
        "profile": {
            "display_name": profile.display_name if profile else None,
            "organisation": profile.organisation if profile else None,
            "share_aggregate": bool(profile.share_aggregate) if profile else False,
            "store_raw_signals": bool(profile.store_raw_signals) if profile else True,
            "allow_baseline": bool(profile.allow_baseline) if profile else True,
            "baseline_min_sessions": profile.baseline_min_sessions if profile else 5,
            "data_note": profile.data_note if profile else None,
        },
    }


def session_dict(session: MonitoringSession, include_analysis: dict | None = None) -> dict[str, Any]:
    data = {
        "id": session.id,
        "user_id": session.user_id,
        "started_at": iso(session.started_at),
        "ended_at": iso(session.ended_at),
        "data_source": session.data_source,
        "scenario": session.scenario,
        "status": session.status,
        "is_simulation": session.is_simulation,
        "is_demo": session.is_demo,
        "duration_seconds": session.duration_seconds,
        "quality_score": session.quality_score,
        "quality_grade": session.quality_grade,
        "has_signal_file": bool(session.signal_file),
    }
    if include_analysis is not None:
        data["latest_analysis"] = include_analysis
    return data


def analysis_dict(analysis: AnalysisResult, include_features: bool = True) -> dict[str, Any]:
    data = {
        "id": analysis.id,
        "user_id": analysis.user_id,
        "session_id": analysis.session_id,
        "dataset_id": analysis.dataset_id,
        "title": analysis.title,
        "source_type": analysis.source_type,
        "source_label": analysis.source_label,
        "model_version": analysis.model_version,
        "predicted_class": analysis.predicted_class,
        "predicted_label": analysis.predicted_label,
        "confidence": analysis.confidence,
        "uncertainty": analysis.uncertainty,
        "stress_score": analysis.stress_score,
        "class_probabilities": _json(analysis.class_probabilities, {}),
        "quality": {
            "score": analysis.quality_score,
            "grade": analysis.quality_grade,
            "issues": _json(analysis.quality_issues, []),
        },
        "imputed_features": _json(analysis.imputed_features, []),
        "explanation": _json(analysis.explanation, {}),
        "window_count": analysis.window_count,
        "duration_seconds": analysis.duration_seconds,
        "notes": analysis.notes,
        "is_demo": analysis.is_demo,
        "created_at": iso(analysis.created_at),
    }
    if include_features:
        data["features"] = _json(analysis.features, {})
    return data


def baseline_dict(baseline: BaselineRecord | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if baseline is None:
        return {"exists": False, **(payload or {})}
    return {
        "exists": True,
        "id": baseline.id,
        "features": _json(baseline.features, {}),
        "session_count": baseline.session_count,
        "session_ids": _json(baseline.session_ids, []),
        "version": baseline.version,
        "created_at": iso(baseline.created_at),
        **(payload or {}),
    }


def dataset_dict(dataset: Dataset, include_meta: bool = True) -> dict[str, Any]:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "source": dataset.source,
        "description": dataset.description,
        "channels": _json(dataset.channels, []),
        "sampling_rates": _json(dataset.sampling_rates, {}),
        "participant_count": dataset.participant_count,
        "label_distribution": _json(dataset.label_distribution, {}),
        "class_names": _json(dataset.class_names, []),
        "is_demo": dataset.is_demo,
        "is_reference": dataset.is_reference,
        "uploaded_by": dataset.uploaded_by,
        "created_at": iso(dataset.created_at),
        **({"file_meta": _json(dataset.file_meta, {})} if include_meta else {}),
    }


def experiment_dict(experiment: ResearchExperiment) -> dict[str, Any]:
    return {
        "id": experiment.id,
        "dataset_id": experiment.dataset_id,
        "model_type": experiment.model_type,
        "evaluation_strategy": experiment.evaluation_strategy,
        "metrics": _json(experiment.metrics, {}),
        "model_version": experiment.model_version,
        "notes": experiment.notes,
        "created_at": iso(experiment.created_at),
    }


def report_dict(report: Report) -> dict[str, Any]:
    return {
        "id": report.id,
        "kind": report.kind,
        "title": report.title,
        "analysis_id": report.analysis_id,
        "experiment_id": report.experiment_id,
        "meta": _json(report.meta, {}),
        "has_file": bool(report.file_path),
        "created_at": iso(report.created_at),
    }
