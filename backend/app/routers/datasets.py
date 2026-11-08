"""Dataset listing and preview endpoints."""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Dataset, User
from ..services.serializers import dataset_dict
from ml.features import CHANNEL_LABELS, detect_channels, features_from_frame

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _visible_datasets(db: Session, user: User) -> list[Dataset]:
    stmt = (
        select(Dataset)
        .where(
            or_(
                Dataset.uploaded_by == user.id,
                Dataset.is_demo.is_(True),
                Dataset.is_reference.is_(True),
            )
        )
        .order_by(Dataset.is_reference.desc(), Dataset.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("")
def list_datasets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {
        "datasets": [dataset_dict(dataset) for dataset in _visible_datasets(db, user)],
    }


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not dataset.is_reference and not dataset.is_demo and dataset.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this dataset.")
    return {"dataset": dataset_dict(dataset)}


@router.get("/{dataset_id}/preview")
def preview_dataset(
    dataset_id: str,
    points: int = 400,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if dataset.is_reference:
        raise HTTPException(
            status_code=400,
            detail="WESAD reference data is not rendered as raw series. Inspect the dataset summary in the Research Centre.",
        )
    if dataset.uploaded_by is not None and dataset.uploaded_by != user.id and not dataset.is_demo:
        raise HTTPException(status_code=403, detail="You do not have access to this dataset.")
    if not dataset.file_path or not Path(dataset.file_path).exists():
        raise HTTPException(status_code=410, detail="Dataset file is no longer available.")

    frame = pd.read_csv(dataset.file_path)
    detected = detect_channels(frame)
    channels = detected["channels"]
    if not channels:
        raise HTTPException(status_code=422, detail="No recognised physiological columns in this dataset.")
    n = max(np.asarray(v).shape[0] for v in channels.values())
    step = max(1, n // max(50, min(points, 1200)))
    preview = {}
    for key, values in channels.items():
        arr = np.asarray(values)[::step]
        if arr.ndim > 1:
            arr = arr[:, 0]
        preview[key] = [None if not np.isfinite(v) else round(float(v), 4) for v in arr]
    parsed = features_from_frame(frame)
    return {
        "dataset": dataset_dict(dataset),
        "preview": preview,
        "channels": [
            {"key": key, "label": CHANNEL_LABELS.get(key, key), "column": detected["columns"].get(key, "")}
            for key in detected["columns"]
        ],
        "mapping": detected["columns"],
        "sampling_rate": parsed["sampling_rate"],
        "sampling_rate_source": parsed["sampling_rate_source"],
        "duration_seconds": round(parsed["duration_seconds"], 1),
        "windows": len(parsed["windows"]),
        "quality": parsed["quality"],
        "rows": int(frame.shape[0]),
        "columns": [str(c) for c in frame.columns[:60]],
    }
