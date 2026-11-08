"""Focused tests for preprocessing, inference, persistence and evaluation.

These tests use synthetic signals and a temporary database; they never touch
the demonstration database or the WESAD installation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.models import Base, Profile, User  # noqa: E402
from app.services import analysis as analysis_service  # noqa: E402
from app.services import inference  # noqa: E402
from app.services.simulation import generate_window  # noqa: E402
from ml.features import (  # noqa: E402
    FEATURE_NAMES,
    assess_quality,
    extract_window_features,
    features_from_frame,
)

ARTIFACTS = BACKEND / "ml" / "artifacts"


def _synthetic_frame(seconds: int = 90, fs: int = 250) -> pd.DataFrame:
    t = np.arange(seconds * fs) / fs
    ecg = 0.05 * np.sin(2 * np.pi * 1.1 * t) + 0.9 * np.exp(
        -np.power(((t * 1.1) % 1 - 0.3) * 14, 2)
    )
    eda = 2.0 + 0.35 * np.sin(2 * np.pi * 0.05 * t) + 0.05 * np.sin(2 * np.pi * 0.25 * t)
    resp = 0.4 * np.sin(2 * np.pi * 0.22 * t)
    return pd.DataFrame(
        {
            "time_s": t,
            "ECG": ecg,
            "EDA": eda,
            "Resp": resp,
            "Temp": 33.0 + 0.05 * np.sin(2 * np.pi * 0.002 * t),
            "ACC_x": 0.01 * np.sin(2 * np.pi * 0.4 * t),
            "ACC_y": 0.01 * np.cos(2 * np.pi * 0.3 * t),
            "ACC_z": np.full_like(t, 0.98),
        }
    )


def test_time_column_sets_sampling_rate_and_windows():
    parsed = features_from_frame(_synthetic_frame())
    assert parsed["sampling_rate"] == 250
    assert "time_s" in parsed["sampling_rate_source"]
    assert parsed["duration_seconds"] == 90
    assert len(parsed["windows"]) == 2
    for window in parsed["windows"]:
        assert set(FEATURE_NAMES).issubset(window["features"].keys())
        assert window["quality"]["score"] is not None


def test_noisy_signal_is_flagged_by_quality():
    window = generate_window("noisy", 0, 60, seed=5)
    quality = assess_quality(window["channels"], window["sampling_rates"], 60.0)
    assert quality["score"] < 85
    codes = {issue["code"] for issue in quality["issues"]}
    assert codes & {"noisy_ecg", "irregular_cardiac", "implausible_cardiac"}


def test_resting_simulation_predicts_neutral_with_calibrated_probabilities():
    window = generate_window("resting", 0, 60, seed=5)
    features = extract_window_features(window["channels"], window["sampling_rates"], 60.0)
    quality = assess_quality(window["channels"], window["sampling_rates"], 60.0)
    result = inference.predict_windows([{"features": features, "quality": quality}])
    assert result["available"] is True
    assert result["predicted_class"] == "neutral"
    assert abs(sum(result["class_probabilities"].values()) - 1.0) < 1e-6
    assert result["confidence"] is not None
    assert result["quality"]["grade"] == "good"


def test_grouped_evaluation_metrics_are_realistic_and_participant_independent():
    metrics = json.loads((ARTIFACTS / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["windows"] == 1032
    assert metrics["participants"] == 15
    assert "GroupKFold" in metrics["evaluation_strategy"]
    assert len(metrics["models"]) >= 3
    best = max(metrics["models"], key=lambda item: item["metrics"]["balanced_accuracy"])
    assert metrics["best_model"] == best["model"]
    assert 0.6 <= best["metrics"]["balanced_accuracy"] < 1.0
    assert len(best["metrics"]["confusion_matrix"]) == 3
    assert len(metrics["feature_importance"]) == len(FEATURE_NAMES)
    assert metrics["best_model_version"]


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    user = User(name="Test User", email="test@example.com", password_hash="x", role="individual")
    user.profile = Profile(display_name="Test User", share_aggregate=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    try:
        yield session, user
    finally:
        session.close()
        engine.dispose()


def test_analysis_is_persisted_with_model_provenance(db_session):
    db, user = db_session
    window = generate_window("arousal", 0, 60, seed=11)
    record, _ = analysis_service.analyse_channels(
        db,
        user,
        window["channels"],
        window["sampling_rates"],
        title="Test arousal window",
        source_type="simulated",
        source_label="Synthetic test window",
        duration=60.0,
        is_demo=True,
    )
    assert record.id
    assert record.model_version
    assert record.predicted_class in {"neutral", "stress", "amusement"}
    assert record.window_count == 1
    assert json.loads(record.class_probabilities)
    explanation = json.loads(record.explanation)
    assert explanation["method_label"]
    assert explanation["local"]
