"""Analysis endpoints: CSV upload, WESAD reference windows, history."""
from __future__ import annotations

import io
import json
import re
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_current_user
from ..models import AnalysisResult, Dataset, User
from ..schemas import DemoAnalysisIn, ReferenceAnalysisIn
from ..services import analysis as analysis_service
from ..services import inference
from ..services.serializers import analysis_dict, dataset_dict
from ml.features import CHANNEL_LABELS, detect_channels, infer_fs

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return cleaned[:120] or "upload.csv"


def _read_frame(contents: bytes) -> pd.DataFrame:
    for kwargs in ({"sep": None, "engine": "python"}, {}):
        try:
            frame = pd.read_csv(io.BytesIO(contents), **kwargs)
            if frame.shape[1] >= 1:
                return frame
        except Exception:
            continue
    raise HTTPException(
        status_code=422,
        detail="The file could not be parsed as CSV. Export a comma- or tab-separated file with a header row.",
    )


def _preview(parsed: dict, points: int = 500) -> dict:
    out = {}
    for name, values in parsed["preview"].items():
        arr = np.asarray(values, dtype=float)
        if arr.size == 0:
            continue
        step = max(1, arr.size // points)
        sampled = arr[::step][:points]
        out[name] = [None if not np.isfinite(v) else round(float(v), 4) for v in sampled]
    return out


def _inspection(parsed: dict, frame: pd.DataFrame, filename: str, contents: bytes) -> dict:
    channel_columns = parsed["channel_columns"]
    channels = [
        {
            "key": key,
            "label": CHANNEL_LABELS.get(key, key),
            "column": parsed["channel_columns"].get(key, ""),
        }
        for key in parsed["channel_columns"]
    ]
    sample_rate = parsed["sampling_rate"]
    return {
        "filename": filename,
        "size_bytes": len(contents),
        "rows": int(frame.shape[0]),
        "columns": [str(c) for c in frame.columns[:80]],
        "column_count": int(frame.shape[1]),
        "channels": channels,
        "sampling_rate": sample_rate,
        "sampling_rate_source": parsed["sampling_rate_source"],
        "duration_seconds": round(parsed["duration_seconds"], 1),
        "n_samples": parsed["n_samples"],
        "windows": len(parsed["windows"]),
        "missing_values": parsed["coverage"]["missing_values"],
        "quality": parsed["quality"],
        "preview": _preview(parsed),
        "preview_seconds": round(min(parsed["duration_seconds"], 12.0), 1),
        "unrecognised_columns": [
            str(c) for c in frame.columns if str(c) not in channel_columns.values()
        ][:12],
    }


@router.post("/upload", status_code=201)
async def upload(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    sampling_rate: float | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or "upload.csv"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".txt", ".tsv"}:
        raise HTTPException(status_code=415, detail="Only .csv, .tsv and .txt files are supported.")
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_bytes / (1024 * 1024):.1f} MB limit.",
        )

    frame = _read_frame(contents)
    if frame.shape[0] < 20:
        raise HTTPException(status_code=422, detail="At least 20 rows are required to analyse a signal.")
    if frame.shape[0] > 400_000:
        raise HTTPException(
            status_code=413,
            detail="This file has more than 400,000 rows. Trim or resample it before uploading.",
        )
    try:
        detected = detect_channels(frame)
    except Exception:
        detected = {"channels": {}, "columns": {}}
    if not detected["channels"]:
        raise HTTPException(
            status_code=422,
            detail=(
                "No recognised physiological columns were found. Expected column names such as ECG, BVP, EDA/GSR, "
                "Resp, Temp, EMG, ACC_x/ACC_y/ACC_z or HR."
            ),
        )

    stored_name = f"{uuid.uuid4().hex}_{_safe_name(filename)}"
    path = settings.storage_dir / "uploads" / stored_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)

    clean_title = (title or Path(filename).stem).strip()[:180] or "Uploaded signal"
    dataset = Dataset(
        name=clean_title,
        source="upload",
        description="User-uploaded physiological signal file.",
        file_path=str(path),
        file_meta=json.dumps(
            {
                "filename": filename,
                "size_bytes": len(contents),
                "rows": int(frame.shape[0]),
                "columns": [str(c) for c in frame.columns],
                "is_simulation": False,
            }
        ),
        channels=json.dumps(sorted(detected["channels"].keys())),
        sampling_rates=json.dumps({"assumed_hz": infer_fs(frame, sampling_rate, detected.get("time_column"))[0]}),
        participant_count=1,
        uploaded_by=user.id,
        is_demo=False,
        is_reference=False,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    try:
        record, parsed = analysis_service.analyse_dataframe(
            db,
            user,
            frame,
            title=clean_title,
            source_type="upload",
            source_label=f"Uploaded file: {filename}",
            fs_hint=sampling_rate,
            dataset_id=dataset.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    inspection = _inspection(parsed, frame, filename, contents)
    return {
        "analysis": analysis_dict(record),
        "dataset": dataset_dict(dataset),
        "inspection": inspection,
        "notice": "Uploaded data analysed. Results describe similarity to WESAD conditions, not a diagnosis.",
    }


@router.post("/reference", status_code=201)
def reference(
    payload: ReferenceAnalysisIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        record, meta = analysis_service.analyse_reference_window(db, user, payload.subject, payload.label)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "analysis": analysis_dict(record),
        "reference": {k: v for k, v in meta.items() if k != "features"},
        "features": meta["features"],
        "notice": (
            "This runs the trained model on a windows whose features were extracted offline from the local WESAD "
            "installation. It demonstrates genuine inference on reference data, not a prediction about you."
        ),
    }


@router.post("/demo", status_code=201)
def demo_analysis(
    payload: DemoAnalysisIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    dataset = db.get(Dataset, payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    if not dataset.is_demo and not dataset.is_reference:
        if dataset.uploaded_by != user.id:
            raise HTTPException(status_code=403, detail="You do not have access to this dataset.")
    if dataset.is_reference:
        try:
            record, meta = analysis_service.analyse_reference_window(db, user, None, None)
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return {"analysis": analysis_dict(record), "dataset": dataset_dict(dataset), "reference": meta}
    if not dataset.file_path or not Path(dataset.file_path).exists():
        raise HTTPException(status_code=410, detail="The dataset file is no longer available on disk.")
    frame = pd.read_csv(dataset.file_path)
    try:
        record, parsed = analysis_service.analyse_dataframe(
            db,
            user,
            frame,
            title=dataset.name,
            source_type="demo_file" if dataset.is_demo else "upload",
            source_label=f"Dataset: {dataset.name} ({dataset.source})",
            dataset_id=dataset.id,
            is_demo=dataset.is_demo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "analysis": analysis_dict(record),
        "dataset": dataset_dict(dataset),
        "inspection": _inspection(parsed, frame, dataset.name, b""),
    }


@router.get("")
def list_analyses(
    limit: int = 30,
    source: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    stmt = select(AnalysisResult).where(AnalysisResult.user_id == user.id)
    if source:
        stmt = stmt.where(AnalysisResult.source_type == source)
    stmt = stmt.order_by(desc(AnalysisResult.created_at)).limit(max(1, min(limit, 200)))
    return {"analyses": [analysis_dict(a, include_features=False) for a in db.scalars(stmt).all()]}


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    record = db.get(AnalysisResult, analysis_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    payload = analysis_dict(record)
    if record.dataset_id:
        dataset = db.get(Dataset, record.dataset_id)
        if dataset:
            payload["dataset"] = dataset_dict(dataset)
    if record.session_id:
        from ..models import MonitoringSession

        session = db.get(MonitoringSession, record.session_id)
        if session:
            payload["session"] = {
                "id": session.id,
                "scenario": session.scenario,
                "is_simulation": session.is_simulation,
                "duration_seconds": session.duration_seconds,
                "status": session.status,
            }
    return payload


@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    record = db.get(AnalysisResult, analysis_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    db.delete(record)
    db.commit()
    return {"ok": True}


@router.get("/{analysis_id}/signal")
def download_signal(
    analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    record = db.get(AnalysisResult, analysis_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    from ..models import MonitoringSession

    if not record.session_id:
        raise HTTPException(status_code=404, detail="This analysis has no stored signal file.")
    session = db.get(MonitoringSession, record.session_id)
    if session is None or not session.signal_file or not Path(session.signal_file).exists():
        raise HTTPException(status_code=404, detail="Signal file was not retained (privacy setting).")
    return FileResponse(session.signal_file, filename=f"{session.id}.csv", media_type="text/csv")
