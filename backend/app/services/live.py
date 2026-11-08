"""Live monitor engine.

The simulated stream is generated server-side so that it passes through the
same preprocessing and inference code as uploaded data.  Signal buffers are
recomputed from a deterministic seed for each tick, which keeps the demo
reproducible and avoids storing raw arrays in relational rows.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AnalysisResult, MonitoringSession, SignalAsset, User
from ml.features import assess_quality, extract_window_features, detect_beats
from . import inference
from .analysis import analyse_channels
from .simulation import FS, generate_window, display_payload, SCENARIOS

_recent: dict[str, list[dict[str, Any]]] = {}


def _state(session: MonitoringSession) -> dict[str, Any]:
    return _recent.setdefault(session.id, [])


def _window_for(session: MonitoringSession, elapsed: float) -> dict[str, Any]:
    seconds = int(min(60, max(4, elapsed)))
    t0 = max(0.0, elapsed - seconds)
    return generate_window(session.scenario, t0, seconds, seed=abs(hash(session.id)) % 100000)


def beat_series(window: dict[str, Any]) -> list[dict[str, float]]:
    ecg = window["channels"]["ecg"]
    try:
        peaks = detect_beats(ecg, FS)
    except Exception:
        return []
    if peaks.size < 2:
        return []
    rr = np.diff(peaks) / FS
    times = (peaks[1:] / FS + window["t0"]).round(1)
    return [
        {"t": float(t), "bpm": round(float(60.0 / r), 1)}
        for t, r in zip(times[-40:], rr[-40:])
        if 0.3 < r < 2.0
    ]


def tick(db: Session, user: User, session: MonitoringSession, tick_seconds: float) -> dict[str, Any]:
    if session.status != "active":
        window = _window_for(session, max(session.duration_seconds, 4))
        return {
            "status": session.status,
            "elapsed_seconds": session.duration_seconds,
            "scenario": session.scenario,
            "is_simulation": True,
            "signal": display_payload(window),
            "prediction": None,
            "prediction_history": _state(session),
            "message": "Session is paused." if session.status == "paused" else "Session has ended.",
        }

    elapsed = float(session.duration_seconds) + float(tick_seconds)
    window = _window_for(session, elapsed)
    channels = window["channels"]
    fs = window["sampling_rates"]
    seconds = window["seconds"]
    features = extract_window_features(channels, fs, seconds)
    quality = assess_quality(channels, fs, seconds)
    prediction = None
    if elapsed >= 30:
        prediction = inference.predict_windows([{"features": features, "quality": quality}])
        entry = {
            "at_seconds": round(elapsed, 1),
            "label": prediction["predicted_label"],
            "predicted_class": prediction["predicted_class"],
            "confidence": prediction["confidence"],
            "stress_probability": prediction["stress_probability"],
            "quality_score": quality["score"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        state = _state(session)
        state.append(entry)
        del state[:-12]
    else:
        prediction = {
            "available": inference.is_available(),
            "predicted_class": None,
            "predicted_label": "Collecting signal",
            "confidence": None,
            "stress_probability": None,
            "class_probabilities": {},
            "quality": quality,
            "windows_used": 1,
            "status": "collecting",
            "message": f"Collecting signal — {max(0, 30 - int(elapsed))}s until the first estimate.",
            "explanation": {},
            "limitations": [],
        }

    session.duration_seconds = int(elapsed)
    session.quality_score = quality["score"]
    session.quality_grade = quality["grade"]
    db.commit()

    return {
        "status": session.status,
        "elapsed_seconds": session.duration_seconds,
        "scenario": session.scenario,
        "scenario_label": SCENARIOS[session.scenario]["label"],
        "is_simulation": True,
        "signal": display_payload(window),
        "hr_series": beat_series(window),
        "prediction": prediction,
        "prediction_history": _state(session),
        "quality": quality,
        "duration_seconds": session.duration_seconds,
    }


def stop(db: Session, user: User, session: MonitoringSession) -> tuple[AnalysisResult, dict[str, Any]]:
    elapsed = max(float(session.duration_seconds), 4.0)
    window = _window_for(session, elapsed)
    channels = window["channels"]
    fs = window["sampling_rates"]
    seconds = window["seconds"]

    if user.profile and user.profile.store_raw_signals:
        path = settings.storage_dir / "sessions" / f"{session.id}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        eda = channels["eda"]
        resp = channels["resp"]
        temp = channels["temp"]
        acc = channels["acc"]
        magnitude = np.sqrt(np.sum(acc**2, axis=1))
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["time_s", "EDA", "Resp", "Temp", "ACC_mag"])
            for idx in range(len(eda)):
                writer.writerow(
                    [
                        round(window["t0"] + idx / 4.0, 2),
                        None if not np.isfinite(eda[idx]) else round(float(eda[idx]), 4),
                        None if not np.isfinite(resp[idx]) else round(float(resp[idx]), 4),
                        None if not np.isfinite(temp[idx]) else round(float(temp[idx]), 4),
                        round(float(magnitude[idx]), 4),
                    ]
                )
        session.signal_file = str(path)
        asset = SignalAsset(
            user_id=user.id,
            session_id=session.id,
            label=f"Simulated session ({session.scenario})",
            file_path=str(path),
            channels=json.dumps(list(channels.keys())),
            sampling_rates=json.dumps({"ecg": FS, "eda": 4, "resp": 4, "temp": 4, "acc": 4}),
            sample_count=len(eda),
            duration_seconds=seconds,
            quality_score=session.quality_score,
            quality_grade=session.quality_grade,
            meta=json.dumps(
                {
                    "is_simulation": True,
                    "scenario": session.scenario,
                    "retained_channels": ["EDA", "Resp", "Temp", "ACC_mag"],
                    "note": "Simulated signals, not measurements from a person.",
                }
            ),
        )
        db.add(asset)

    analysis, _ = analyse_channels(
        db,
        user,
        channels,
        fs,
        title=f"Simulated monitoring session — {SCENARIOS[session.scenario]['label']}",
        source_type="simulated",
        source_label=(
            f"Simulated {session.scenario} scenario ({seconds:.0f}s window). "
            "Illustrative synthetic signals, not a real measurement."
        ),
        duration=seconds,
        session_id=session.id,
        is_demo=session.is_demo,
    )
    session.status = "completed"
    session.ended_at = datetime.now(timezone.utc)
    session.quality_score = analysis.quality_score
    session.quality_grade = analysis.quality_grade
    db.commit()
    _recent.pop(session.id, None)
    return analysis, {"window": window, "prediction": None}
