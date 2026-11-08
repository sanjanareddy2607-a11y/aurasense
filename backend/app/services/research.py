"""Live research experiments on cached WESAD window features."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sqlalchemy.orm import Session

from ..models import Dataset, ResearchExperiment, User
from ml.train import LABEL_ORDER, _metrics as compute_metrics, build_models


def features_path() -> Path:
    from ..config import settings

    return settings.artifacts_dir / "wesad_features.csv"


def dataset_available() -> bool:
    return features_path().exists()


def run_experiment(db: Session, user: User, dataset: Dataset, model_name: str) -> ResearchExperiment:
    path = features_path()
    if not path.exists():
        raise ValueError(
            "The WESAD feature table is not available. Run `python -m ml.wesad_extract` in the backend."
        )
    data = pd.read_csv(path)
    from ml.features import FEATURE_NAMES

    missing = [name for name in FEATURE_NAMES if name not in data.columns]
    if missing:
        raise ValueError(f"Feature table is missing columns: {missing}")

    data = data.dropna(subset=["label", "subject"])
    X = data[FEATURE_NAMES].to_numpy(dtype=float)
    codes = {name: i for i, name in enumerate(LABEL_ORDER)}
    try:
        y = np.array([codes[label] for label in data["label"]], dtype=int)
    except KeyError as exc:
        raise ValueError(f"Unexpected label in feature table: {exc}") from exc
    groups = data["subject"].to_numpy()

    models = build_models()
    if model_name not in models:
        raise ValueError(
            f"{model_name} is not installed in this environment. Available: {', '.join(models)}."
        )
    model = models[model_name]
    n_splits = min(3, len(np.unique(groups)))
    splitter = GroupKFold(n_splits=n_splits)
    oof = np.full(len(y), -1, dtype=int)
    fold_scores = []
    for train_idx, test_idx in splitter.split(X, y, groups):
        model.fit(X[train_idx], y[train_idx])
        pred = model.predict(X[test_idx])
        oof[test_idx] = pred
        fold_scores.append(
            round(float((pred == y[test_idx]).mean()), 4)
        )

    metrics = compute_metrics(y, oof, list(range(len(LABEL_ORDER))))
    per_subject = {}
    for subject in np.unique(groups):
        mask = groups == subject
        if mask.sum() >= 5:
            per_subject[str(subject)] = {
                "accuracy": round(float((oof[mask] == y[mask]).mean()), 4),
                "windows": int(mask.sum()),
            }

    version = "exp-" + hashlib.sha1(
        f"{model_name}-{len(y)}-{datetime.now(timezone.utc).timestamp()}".encode()
    ).hexdigest()[:8]
    payload = {
        **metrics,
        "model": model_name,
        "evaluation_strategy": f"{n_splits}-fold GroupKFold by participant",
        "windows": int(len(y)),
        "participants": int(len(np.unique(groups))),
        "class_distribution": {k: int(v) for k, v in data["label"].value_counts().to_dict().items()},
        "fold_accuracies": fold_scores,
        "per_subject": per_subject,
        "run_by": user.email,
    }
    experiment = ResearchExperiment(
        dataset_id=dataset.id,
        model_type=model_name,
        evaluation_strategy=payload["evaluation_strategy"],
        metrics=json.dumps(payload),
        model_version=version,
        notes="Experiment executed from the Research Centre on cached WESAD features.",
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment
