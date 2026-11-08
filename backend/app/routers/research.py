"""Research Centre endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Dataset, ResearchExperiment, User
from ..schemas import ExperimentIn
from ..services import inference, research
from ..services.serializers import dataset_dict, experiment_dict
from ml.features import FEATURE_META

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    metrics = inference.load_metrics()
    artifact_summary = None
    summary_path = inference.ARTIFACTS / "dataset_summary.json"
    if summary_path.exists():
        try:
            artifact_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            artifact_summary = None

    dataset = db.scalars(select(Dataset).where(Dataset.is_reference.is_(True))).first()
    experiments = db.scalars(
        select(ResearchExperiment).order_by(desc(ResearchExperiment.created_at)).limit(20)
    ).all()
    model = inference.load_artifact()

    return {
        "dataset": dataset_dict(dataset) if dataset else None,
        "dataset_summary": artifact_summary,
        "metrics": metrics,
        "model": {
            "available": bool(model),
            "name": model.get("model_name") if model else None,
            "version": model.get("model_version") if model else None,
            "trained_at": model.get("trained_at") if model else None,
            "cv_strategy": model.get("cv_strategy") if model else None,
            "training_windows": model.get("training_windows") if model else None,
            "participants": model.get("participants") if model else None,
            "global_metrics": model.get("global_metrics") if model else None,
            "feature_importance": model.get("feature_importance") if model else None,
        } if model else {"available": False},
        "features": [{"name": name, **FEATURE_META.get(name, {})} for name in (model.get("feature_names") if model else FEATURE_META.keys())],
        "experiments": [experiment_dict(e) for e in experiments],
        "can_run_experiments": user.role in ("researcher", "admin"),
        "availability": {
            "feature_table": research.dataset_available(),
            "trained_model": bool(model),
        },
        "citation": "Schmidt, P., & Reiss, A. (2018). WESAD (Wearable Stress and Affect Detection). DOI: 10.24432/C57K5T",
        "dataset_url": "https://archive.ics.uci.edu/dataset/465/wesad+wearable+stress+and+affect+detect",
        "paper_url": "https://www.eti.uni-siegen.de/ubicomp/papers/ubi_icmi2018.pdf",
    }


@router.get("/experiments")
def list_experiments(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(ResearchExperiment).order_by(desc(ResearchExperiment.created_at)).limit(50)
    ).all()
    return {"experiments": [experiment_dict(e) for e in rows]}


@router.get("/experiments/{experiment_id}")
def get_experiment(
    experiment_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    experiment = db.get(ResearchExperiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return experiment_dict(experiment)


@router.post("/experiments", status_code=201)
def create_experiment(
    payload: ExperimentIn,
    user: User = Depends(require_roles("researcher", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    dataset = db.get(Dataset, payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    try:
        experiment = research.run_experiment(db, user, dataset, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "experiment": experiment_dict(experiment),
        "notice": "Experiment executed with participant-independent GroupKFold evaluation on the cached WESAD features.",
    }


@router.get("/metrics")
def metrics(user: User = Depends(get_current_user)) -> dict:
    payload = inference.load_metrics()
    if payload is None:
        raise HTTPException(
            status_code=503,
            detail="Evaluation metrics are not available. Run `python -m ml.train` in the backend.",
        )
    return payload


@router.get("/datasets")
def research_datasets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(Dataset).where(or_(Dataset.is_reference.is_(True), Dataset.is_demo.is_(True)))
    ).all()
    return {"datasets": [dataset_dict(d) for d in rows]}
