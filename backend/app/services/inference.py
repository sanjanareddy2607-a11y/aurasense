"""Model loading, inference and local explanation."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ..config import settings
from ml.features import FEATURE_META, FEATURE_NAMES

ARTIFACTS = settings.artifacts_dir
MODEL_PATH = ARTIFACTS / "model.joblib"
METRICS_PATH = ARTIFACTS / "metrics.json"

CLASS_LABELS = {
    "neutral": "Neutral-associated pattern",
    "stress": "Stress-associated pattern",
    "amusement": "Amusement / positive-affect pattern",
}
CLASS_COPY = {
    "neutral": "Features in this window most resemble the neutral (baseline) recordings in the reference dataset.",
    "stress": "Features in this window most resemble the stress-condition recordings in the reference dataset. This is a pattern similarity estimate, not a diagnosis.",
    "amusement": "Features in this window most resemble the amusement (positive-affect) recordings in the reference dataset.",
}
INSUFFICIENT_LABEL = "Insufficient signal quality"

_lock = threading.Lock()
_cache: dict[str, Any] = {"mtime": 0.0, "artifact": None}


def load_artifact(force: bool = False) -> dict[str, Any] | None:
    if not MODEL_PATH.exists():
        return None
    mtime = MODEL_PATH.stat().st_mtime
    with _lock:
        if not force and _cache["artifact"] is not None and _cache["mtime"] == mtime:
            return _cache["artifact"]
        artifact = joblib.load(MODEL_PATH)
        _cache["artifact"] = artifact
        _cache["mtime"] = mtime
        return artifact


def load_metrics() -> dict[str, Any] | None:
    if not METRICS_PATH.exists():
        return None
    try:
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def is_available() -> bool:
    return MODEL_PATH.exists()


def _weighted_features(windows: list[dict[str, Any]]) -> tuple[np.ndarray, list[str], float]:
    feature_names = FEATURE_NAMES
    vectors = []
    weights = []
    imputed_counts = {name: 0 for name in feature_names}
    for window in windows:
        feats = window["features"]
        vector = []
        for name in feature_names:
            value = feats.get(name)
            if value is None or not np.isfinite(value):
                vector.append(np.nan)
                imputed_counts[name] += 1
            else:
                vector.append(float(value))
        vectors.append(vector)
        weights.append(max(0.05, float(window.get("quality", {}).get("score", 50.0)) / 100.0))
    matrix = np.asarray(vectors, dtype=float)
    weight_array = np.asarray(weights, dtype=float)
    weight_array = weight_array / weight_array.sum()
    imputed = [name for name, count in imputed_counts.items() if count / max(len(windows), 1) > 0.5]
    # Quality-weighted mean ignoring NaNs.
    aggregated = np.full(len(feature_names), np.nan)
    for idx in range(len(feature_names)):
        column = matrix[:, idx]
        mask = np.isfinite(column)
        if mask.any():
            aggregated[idx] = float(np.sum(column[mask] * weight_array[mask]) / np.sum(weight_array[mask]))
    coverage = 1.0 - (len(imputed) / len(feature_names))
    return aggregated, imputed, coverage


def _predict_proba(model, artifact: dict[str, Any], vector: np.ndarray) -> np.ndarray:
    impute = artifact.get("impute_values", {})
    filled = np.array(
        [
            value if np.isfinite(value) else float(impute.get(name, 0.0))
            for value, name in zip(vector, artifact.get("feature_names", FEATURE_NAMES))
        ],
        dtype=float,
    )
    return np.asarray(model.predict_proba(filled.reshape(1, -1)))[0]


def _local_contributions(
    artifact: dict[str, Any],
    vector: np.ndarray,
    probabilities: np.ndarray,
    top_class: int,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Model-agnostic occlusion contributions.

    Each feature is replaced with its training median and the change in the
    predicted-class probability is recorded.  This is a local surrogate for
    behaviour, not a causal inference.  SHAP is not installed in this
    environment, so this cheaper, transparent method is used and labelled as
    such in the UI and reports.
    """
    model = artifact["model"]
    names = artifact["feature_names"]
    impute = artifact["impute_values"]
    base = np.array(
        [v if np.isfinite(v) else impute.get(n, 0.0) for v, n in zip(vector, names)], dtype=float
    )
    base_prob = float(probabilities[top_class])
    contributions = []
    for idx, name in enumerate(names):
        probe = base.copy()
        probe[idx] = float(impute.get(name, 0.0))
        try:
            prob = float(np.asarray(model.predict_proba(probe.reshape(1, -1)))[0][top_class])
        except Exception:
            continue
        delta = base_prob - prob
        contributions.append(
            {
                "feature": name,
                "label": FEATURE_META.get(name, {}).get("label", name),
                "unit": FEATURE_META.get(name, {}).get("unit", ""),
                "group": FEATURE_META.get(name, {}).get("group", ""),
                "value": round(float(base[idx]), 4),
                "reference_median": round(float(impute.get(name, 0.0)), 4),
                "contribution": round(delta, 5),
                "direction": "toward" if delta >= 0 else "away",
            }
        )
    contributions.sort(key=lambda item: abs(item["contribution"]), reverse=True)
    return contributions[:limit]


def _aggregate_quality(windows: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(w.get("quality", {}).get("score", 0.0)) for w in windows]
    mean = float(np.mean(scores)) if scores else 0.0
    issues: list[dict[str, str]] = []
    seen = set()
    for window in windows:
        for issue in window.get("quality", {}).get("issues", []):
            key = issue.get("message", "")
            if key not in seen:
                seen.add(key)
                issues.append(issue)
    grade = "insufficient"
    for threshold, name in ((80, "good"), (60, "fair"), (40, "poor")):
        if mean >= threshold:
            grade = name
            break
    return {
        "score": round(mean, 1),
        "grade": grade,
        "issues": issues[:8],
        "window_scores": [round(s, 1) for s in scores[:30]],
    }


def predict_windows(windows: list[dict[str, Any]]) -> dict[str, Any]:
    """Run inference over one or more feature windows and aggregate the result."""
    artifact = load_artifact()
    quality = _aggregate_quality(windows)
    base = {
        "available": bool(artifact),
        "quality": quality,
        "windows_used": len(windows),
        "limitations": [
            "Estimates describe similarity to patterns learned from a laboratory dataset (WESAD) and are not medical conclusions.",
            "Physical activity, caffeine, illness and environmental conditions can produce similar physiological changes.",
            "Feature attributions describe model behaviour, not the biological cause of a response.",
        ],
    }
    if not artifact:
        return {
            **base,
            "predicted_class": None,
            "predicted_label": "Model not trained",
            "confidence": None,
            "uncertainty": None,
            "stress_probability": None,
            "class_probabilities": {},
            "explanation": {},
            "feature_coverage": 0.0,
            "imputed_features": [],
            "status": "model_unavailable",
            "message": "No trained model artefact is installed. Run `python -m ml.train` in the backend.",
        }

    if not windows:
        return {
            **base,
            "predicted_class": None,
            "predicted_label": INSUFFICIENT_LABEL,
            "confidence": None,
            "uncertainty": None,
            "stress_probability": None,
            "class_probabilities": {},
            "explanation": {},
            "feature_coverage": 0.0,
            "imputed_features": [],
            "status": "insufficient",
            "message": "No signal windows were available.",
        }

    vector, imputed, coverage = _weighted_features(windows)
    classes: list[str] = artifact.get("classes", ["neutral", "stress", "amusement"])
    model = artifact["model"]

    # Per-window probabilities, weighted by signal quality.
    prob_matrix = []
    weights = []
    for window in windows:
        feats = window["features"]
        row = np.array(
            [feats.get(name, np.nan) for name in artifact["feature_names"]], dtype=float
        )
        prob_matrix.append(_predict_proba(model, artifact, row))
        weights.append(max(0.05, float(window.get("quality", {}).get("score", 50.0)) / 100.0))
    prob_matrix = np.vstack(prob_matrix)
    weights_arr = np.asarray(weights, dtype=float)
    weights_arr = weights_arr / weights_arr.sum()
    probabilities = np.sum(prob_matrix * weights_arr[:, None], axis=0)

    top_class = int(np.argmax(probabilities))
    predicted_class = classes[top_class]
    confidence = float(probabilities[top_class])
    entropy = float(-np.sum(probabilities * np.log(probabilities + 1e-12)) / np.log(len(classes)))

    cardiac_imputed = "hr_mean" in imputed
    eda_imputed = "eda_mean" in imputed
    reliable = quality["score"] >= 40 and not (cardiac_imputed and eda_imputed)

    explanation = {
        "method": "occlusion",
        "method_label": "Occlusion contribution analysis (model-agnostic)",
        "note": "Each feature is replaced with its training median; the resulting change in the predicted-class probability is shown. SHAP is not available in this environment, so this transparent surrogate is used instead.",
        "global_top": artifact.get("feature_importance", [])[:8],
        "local": _local_contributions(artifact, vector, probabilities, top_class),
        "reference": artifact.get("reference", {}),
    }

    payload = {
        **base,
        "model_name": artifact.get("model_name"),
        "model_version": artifact.get("model_version"),
        "predicted_class": predicted_class if reliable else None,
        "predicted_label": CLASS_LABELS.get(predicted_class, predicted_class) if reliable else INSUFFICIENT_LABEL,
        "class_copy": CLASS_COPY.get(predicted_class, "") if reliable else "",
        "confidence": round(confidence, 4) if reliable else None,
        "uncertainty": round(entropy, 4) if reliable else None,
        "stress_probability": round(float(probabilities[classes.index("stress")]) * 100, 1)
        if "stress" in classes
        else None,
        "class_probabilities": {
            name: round(float(prob), 4) for name, prob in zip(classes, probabilities)
        },
        "quality": quality,
        "status": "ok" if reliable else "insufficient",
        "message": None
        if reliable
        else "Signal quality is too low for a responsible classification. Collect a longer, cleaner recording.",
        "imputed_features": imputed,
        "feature_coverage": round(coverage, 3),
        "features": {
            name: (round(float(value), 4) if np.isfinite(value) else None)
            for name, value in zip(artifact["feature_names"], vector)
        },
        "explanation": explanation,
        "window_count": len(windows),
    }
    return payload


def model_info() -> dict[str, Any]:
    artifact = load_artifact()
    metrics = load_metrics()
    if not artifact:
        return {
            "available": False,
            "message": "Model artefact not found. Train the model with `python -m ml.train`.",
            "metrics": metrics,
            "classes": CLASS_LABELS,
            "features": [
                {"name": name, **FEATURE_META.get(name, {})} for name in FEATURE_NAMES
            ],
        }
    return {
        "available": True,
        "model_name": artifact.get("model_name"),
        "model_version": artifact.get("model_version"),
        "trained_at": artifact.get("trained_at"),
        "training_windows": artifact.get("training_windows"),
        "participants": artifact.get("participants"),
        "cv_strategy": artifact.get("cv_strategy"),
        "classes": CLASS_LABELS,
        "label_mapping": artifact.get("label_mapping"),
        "global_metrics": artifact.get("global_metrics"),
        "feature_importance": artifact.get("feature_importance"),
        "feature_names": artifact.get("feature_names"),
        "features": [
            {"name": name, **FEATURE_META.get(name, {})} for name in artifact.get("feature_names", FEATURE_NAMES)
        ],
        "metrics": metrics,
    }
