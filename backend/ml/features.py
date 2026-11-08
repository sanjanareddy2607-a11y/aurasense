"""Signal preprocessing and feature extraction.

This module is shared by the offline WESAD training pipeline, the CSV analysis
endpoint and the simulated live monitor, so every input passes through the same
code path.

Design notes / limitations
--------------------------
* WESAD chest signals are sampled at 700 Hz, wrist BVP at 64 Hz and wrist
  EDA/temperature at 4 Hz.  Feature functions therefore require an explicit
  sampling rate per channel.
* Cardiac features require beat detection; when fewer than ~6 beats are found
  the cardiac features are returned as NaN and later imputed, and the quality
  layer reports reduced confidence.
* Frequency-domain HRV is deliberately not computed: 60 s windows give too few
  beats for a trustworthy LF/HF estimate.
* EDA "tonic" is estimated with a 10 s moving average rather than a full
  cvxEDA/deconvolution model; this is a documented simplification.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
from scipy import signal as sps
from scipy.ndimage import uniform_filter1d

FEATURE_NAMES: list[str] = [
    "hr_mean",
    "hr_std",
    "rmssd",
    "sdnn",
    "pnn50",
    "eda_mean",
    "eda_std",
    "eda_slope",
    "eda_phasic_std",
    "scr_count",
    "scr_amp_sum",
    "resp_rate",
    "resp_rate_std",
    "resp_amp",
    "temp_mean",
    "temp_std",
    "temp_slope",
    "emg_rms",
    "acc_mag_mean",
    "acc_mag_std",
]

FEATURE_META: dict[str, dict[str, str]] = {
    "hr_mean": {"label": "Mean heart rate", "unit": "bpm", "group": "Cardiac"},
    "hr_std": {"label": "Heart-rate variability (SD of HR)", "unit": "bpm", "group": "Cardiac"},
    "rmssd": {"label": "RMSSD", "unit": "ms", "group": "Cardiac"},
    "sdnn": {"label": "SDNN", "unit": "ms", "group": "Cardiac"},
    "pnn50": {"label": "pNN50", "unit": "%", "group": "Cardiac"},
    "eda_mean": {"label": "Mean skin conductance", "unit": "µS", "group": "Electrodermal"},
    "eda_std": {"label": "Skin-conductance variability", "unit": "µS", "group": "Electrodermal"},
    "eda_slope": {"label": "Skin-conductance trend", "unit": "µS/s", "group": "Electrodermal"},
    "eda_phasic_std": {"label": "Phasic EDA variability", "unit": "µS", "group": "Electrodermal"},
    "scr_count": {"label": "Skin-conductance responses", "unit": "per min", "group": "Electrodermal"},
    "scr_amp_sum": {"label": "SCR amplitude sum", "unit": "µS", "group": "Electrodermal"},
    "resp_rate": {"label": "Respiration rate", "unit": "breaths/min", "group": "Respiration"},
    "resp_rate_std": {"label": "Breathing-rate variability", "unit": "breaths/min", "group": "Respiration"},
    "resp_amp": {"label": "Respiration amplitude", "unit": "a.u.", "group": "Respiration"},
    "temp_mean": {"label": "Mean skin temperature", "unit": "°C", "group": "Temperature"},
    "temp_std": {"label": "Temperature variability", "unit": "°C", "group": "Temperature"},
    "temp_slope": {"label": "Temperature trend", "unit": "°C/min", "group": "Temperature"},
    "emg_rms": {"label": "Muscle activity (RMS)", "unit": "a.u.", "group": "Muscle / motion"},
    "acc_mag_mean": {"label": "Movement magnitude", "unit": "g", "group": "Muscle / motion"},
    "acc_mag_std": {"label": "Movement variability", "unit": "g", "group": "Muscle / motion"},
}

CHANNEL_LABELS: dict[str, str] = {
    "ecg": "ECG (chest)",
    "bvp": "Blood volume pulse (wrist)",
    "eda": "Electrodermal activity",
    "resp": "Respiration",
    "temp": "Skin temperature",
    "emg": "EMG (chest)",
    "acc": "Accelerometer",
    "hr": "Heart-rate series",
}

# Channels used by the quality layer, with how critical each one is for the model.
EXPECTED_CHANNELS: dict[str, int] = {"cardiac": 18, "eda": 14, "resp": 7, "temp": 4, "motion": 3}

WESAD_CHANNEL_FS: dict[str, dict[str, float]] = {
    "chest": {"acc": 700.0, "ecg": 700.0, "emg": 700.0, "eda": 700.0, "temp": 700.0, "resp": 700.0},
    "wrist": {"acc": 32.0, "bvp": 64.0, "eda": 4.0, "temp": 4.0},
}

NON_TARGET_LABELS = {0: "not defined", 4: "meditation", 5: "not defined", 6: "not defined", 7: "not defined"}
WESAD_LABEL_NAMES = {1: "neutral", 2: "stress", 3: "amusement"}


# --------------------------------------------------------------------------- #
# Low-level helpers
# --------------------------------------------------------------------------- #
def clean_array(values: Any) -> np.ndarray:
    """Return a 1-D float array with non-finite values linearly interpolated."""
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        return arr
    finite = np.isfinite(arr)
    if not finite.all():
        if finite.sum() < 2:
            return np.array([])
        idx = np.arange(arr.size)
        arr = np.interp(idx, idx[finite], arr[finite])
    return arr


def _bandpass(x: np.ndarray, fs: float, low: float, high: float, order: int = 3) -> np.ndarray:
    if x.size < 16 or fs <= 0:
        return np.array([])
    nyq = fs / 2.0
    low = max(low, 0.005)
    high = min(high, nyq * 0.92)
    if low >= high:
        return x - np.mean(x)
    try:
        sos = sps.butter(order, [low / nyq, high / nyq], btype="bandpass", output="sos")
        return sps.sosfiltfilt(sos, x)
    except ValueError:
        return x - np.mean(x)


def _safe_slope(y: np.ndarray, fs: float) -> float:
    if y.size < 10 or fs <= 0:
        return float("nan")
    t = np.arange(y.size) / fs
    try:
        return float(np.polyfit(t, y, 1)[0])
    except np.linalg.LinAlgError:
        return float("nan")


def _flat(x: np.ndarray) -> bool:
    return x.size > 0 and float(np.ptp(x)) <= 1e-9


# --------------------------------------------------------------------------- #
# Cardiac
# --------------------------------------------------------------------------- #
def detect_beats(x: np.ndarray, fs: float) -> np.ndarray:
    """Detect R-peaks (ECG) or systolic peaks (BVP), choosing the best polarity."""
    x = clean_array(x)
    if x.size < int(fs * 3) or fs <= 0:
        return np.array([], dtype=int)
    filtered = _bandpass(x, fs, 0.5, min(45.0, fs * 0.45), order=2)
    if filtered.size == 0:
        return np.array([], dtype=int)

    distance = max(1, int(0.28 * fs))
    best: np.ndarray | None = None
    best_score = -np.inf
    for polarity in (1.0, -1.0):
        sig = filtered if polarity > 0 else -filtered
        prominence = max(0.35 * float(np.std(sig)), 1e-12)
        peaks, _ = sps.find_peaks(sig, distance=distance, prominence=prominence)
        if peaks.size < 6:
            continue
        rr = np.diff(peaks) / fs
        rr = rr[(rr > 0.3) & (rr < 2.0)]
        if rr.size < 5:
            continue
        hr = 60.0 / float(np.median(rr))
        if not 35.0 <= hr <= 190.0:
            continue
        score = -float(np.std(rr) / max(np.mean(rr), 1e-9))
        score += min(0.15, peaks.size / (fs * 20))
        if score > best_score:
            best_score = score
            best = peaks
    return best if best is not None else np.array([], dtype=int)


def cardiac_features(x: np.ndarray, fs: float) -> dict[str, float]:
    out = {k: float("nan") for k in ("hr_mean", "hr_std", "rmssd", "sdnn", "pnn50")}
    peaks = detect_beats(x, fs)
    if peaks.size < 7:
        return out
    rr = np.diff(peaks) / fs * 1000.0
    rr = rr[(rr >= 300) & (rr <= 2000)]
    if rr.size < 5:
        return out
    inst_hr = 60000.0 / rr
    diffs = np.diff(rr)
    out["hr_mean"] = float(np.mean(inst_hr))
    out["hr_std"] = float(np.std(inst_hr, ddof=1)) if inst_hr.size > 1 else float("nan")
    out["rmssd"] = float(np.sqrt(np.mean(diffs**2))) if diffs.size else float("nan")
    out["sdnn"] = float(np.std(rr, ddof=1)) if rr.size > 1 else float("nan")
    out["pnn50"] = 100.0 * float(np.mean(np.abs(diffs) > 50)) if diffs.size else float("nan")
    return out


# --------------------------------------------------------------------------- #
# Electrodermal / respiration / temperature / muscle / motion
# --------------------------------------------------------------------------- #
def eda_features(x: np.ndarray, fs: float) -> dict[str, float]:
    x = clean_array(x)
    keys = ("eda_mean", "eda_std", "eda_slope", "eda_phasic_std", "scr_count", "scr_amp_sum")
    out = {k: float("nan") for k in keys}
    if x.size < 5 or fs <= 0:
        return out
    window = max(1, int(fs * 10.0))
    tonic = uniform_filter1d(x, size=min(window, max(1, x.size)), mode="nearest")
    phasic = x - tonic
    duration_min = x.size / fs / 60.0

    out["eda_mean"] = float(np.mean(x))
    out["eda_std"] = float(np.std(x, ddof=1)) if x.size > 1 else float("nan")
    out["eda_slope"] = _safe_slope(x, fs)
    out["eda_phasic_std"] = float(np.std(phasic, ddof=1)) if phasic.size > 1 else float("nan")

    if x.size >= int(fs * 5) and duration_min > 0:
        prominence = max(0.008, 0.25 * float(np.std(phasic)))
        peaks, props = sps.find_peaks(
            phasic, distance=max(1, int(fs * 1.0)), prominence=prominence
        )
        out["scr_count"] = float(peaks.size / duration_min) if peaks.size else 0.0
        heights = props.get("prominences")
        out["scr_amp_sum"] = float(np.sum(heights)) if heights is not None and heights.size else 0.0
    return out


def resp_features(x: np.ndarray, fs: float) -> dict[str, float]:
    x = clean_array(x)
    out = {"resp_rate": float("nan"), "resp_rate_std": float("nan"), "resp_amp": float("nan")}
    if x.size < 10 or fs <= 0:
        return out
    filtered = _bandpass(x, fs, 0.05, 0.6, order=2)
    if filtered.size < 10:
        filtered = x - np.mean(x)
    out["resp_amp"] = float(np.percentile(filtered, 95) - np.percentile(filtered, 5))
    peaks, _ = sps.find_peaks(
        filtered,
        distance=max(1, int(fs * 1.2)),
        prominence=max(0.15 * float(np.std(filtered)), 1e-12),
    )
    if peaks.size >= 3:
        intervals = np.diff(peaks) / fs
        intervals = intervals[(intervals > 1.0) & (intervals < 12.0)]
        if intervals.size >= 2:
            rates = 60.0 / intervals
            out["resp_rate"] = float(60.0 / float(np.median(intervals)))
            out["resp_rate_std"] = float(np.std(rates, ddof=1))
    return out


def temp_features(x: np.ndarray, fs: float) -> dict[str, float]:
    x = clean_array(x)
    out = {"temp_mean": float("nan"), "temp_std": float("nan"), "temp_slope": float("nan")}
    if x.size < 5 or fs <= 0:
        return out
    out["temp_mean"] = float(np.mean(x))
    out["temp_std"] = float(np.std(x, ddof=1)) if x.size > 1 else float("nan")
    slope_per_sec = _safe_slope(x, fs)
    out["temp_slope"] = slope_per_sec * 60.0 if np.isfinite(slope_per_sec) else float("nan")
    return out


def emg_features(x: np.ndarray, fs: float) -> dict[str, float]:
    x = clean_array(x)
    if x.size < 5:
        return {"emg_rms": float("nan")}
    if fs >= 200:
        filtered = _bandpass(x, fs, 20.0, min(95.0, fs * 0.45), order=2)
        if filtered.size == 0:
            filtered = x - np.mean(x)
        rms = float(np.sqrt(np.mean(filtered**2)))
    else:
        rms = float(np.std(np.diff(x)))
    return {"emg_rms": rms}


def motion_features(acc: np.ndarray) -> dict[str, float]:
    out = {"acc_mag_mean": float("nan"), "acc_mag_std": float("nan")}
    arr = np.asarray(acc, dtype=float)
    if arr.size == 0:
        return out
    if arr.ndim == 1:
        magnitude = clean_array(arr)
    elif arr.ndim == 2:
        if arr.shape[1] < 3:
            return out
        arr = np.nan_to_num(arr, nan=0.0)
        magnitude = np.sqrt(np.sum(arr[:, :3] ** 2, axis=1))
    else:
        return out
    if magnitude.size < 5:
        return out
    out["acc_mag_mean"] = float(np.mean(magnitude))
    out["acc_mag_std"] = float(np.std(magnitude, ddof=1))
    return out


# --------------------------------------------------------------------------- #
# Combined extraction
# --------------------------------------------------------------------------- #
def _fs_for(fs: float | dict[str, float], key: str) -> float:
    if isinstance(fs, dict):
        return float(fs.get(key, fs.get("_default", 0.0)) or 0.0)
    return float(fs)


def extract_window_features(
    channels: dict[str, Any],
    fs: float | dict[str, float],
    duration: float | None = None,
) -> dict[str, float]:
    """Extract the fixed 20-feature vector for one signal window.

    ``channels`` accepts ``ecg``, ``bvp``, ``eda``, ``resp``, ``temp``, ``emg``,
    ``acc`` (Nx3 or N,) and ``hr`` (already derived heart rate).  Missing
    channels produce NaN features, which the inference layer imputes and flags.
    """
    features: dict[str, float] = {name: float("nan") for name in FEATURE_NAMES}

    cardiac_source = channels.get("ecg")
    cardiac_key = "ecg"
    if cardiac_source is None or np.asarray(cardiac_source).size == 0:
        cardiac_source = channels.get("bvp")
        cardiac_key = "bvp"

    if cardiac_source is not None and np.asarray(cardiac_source).size:
        features.update(cardiac_features(np.asarray(cardiac_source), _fs_for(fs, cardiac_key)))
    elif channels.get("hr") is not None and np.asarray(channels["hr"]).size > 1:
        hr = clean_array(channels["hr"])
        features["hr_mean"] = float(np.mean(hr))
        features["hr_std"] = float(np.std(hr, ddof=1)) if hr.size > 1 else float("nan")

    if channels.get("eda") is not None and np.asarray(channels["eda"]).size:
        features.update(eda_features(np.asarray(channels["eda"]), _fs_for(fs, "eda")))

    if channels.get("resp") is not None and np.asarray(channels["resp"]).size:
        features.update(resp_features(np.asarray(channels["resp"]), _fs_for(fs, "resp")))

    if channels.get("temp") is not None and np.asarray(channels["temp"]).size:
        features.update(temp_features(np.asarray(channels["temp"]), _fs_for(fs, "temp")))

    if channels.get("emg") is not None and np.asarray(channels["emg"]).size:
        features.update(emg_features(np.asarray(channels["emg"]), _fs_for(fs, "emg")))

    if channels.get("acc") is not None and np.asarray(channels["acc"]).size:
        features.update(motion_features(np.asarray(channels["acc"])))

    if duration and duration > 0:
        # Normalise count-like features so windows of different lengths compare.
        if np.isfinite(features.get("scr_count", np.nan)):
            features["scr_count"] = float(features["scr_count"])

    return {k: (float(v) if np.isfinite(v) else float("nan")) for k, v in features.items()}


# --------------------------------------------------------------------------- #
# Signal quality
# --------------------------------------------------------------------------- #
def _missing_fraction(values: np.ndarray) -> float:
    if values.size == 0:
        return 1.0
    return float(np.mean(~np.isfinite(np.asarray(values, dtype=float))))


def _noise_ratio(values: np.ndarray, fs: float) -> float:
    """Rough high-frequency / total energy ratio for cardiac-like signals."""
    x = clean_array(values)
    if x.size < 32 or fs <= 0:
        return 0.0
    diff = np.diff(x)
    denom = float(np.std(x)) + 1e-9
    return float(np.std(diff) / denom)


def assess_quality(
    channels: dict[str, Any],
    fs: float | dict[str, float],
    duration: float | None = None,
    *,
    require_raw_channels: bool = False,
) -> dict[str, Any]:
    """Score signal adequacy for model inference (0-100)."""
    issues: list[dict[str, str]] = []
    score = 100.0
    present: list[str] = []
    missing: list[str] = []

    groups = {
        "cardiac": [k for k in ("ecg", "bvp", "hr") if channels.get(k) is not None and np.asarray(channels[k]).size],
        "eda": ["eda"] if channels.get("eda") is not None and np.asarray(channels["eda"]).size else [],
        "resp": ["resp"] if channels.get("resp") is not None and np.asarray(channels["resp"]).size else [],
        "temp": ["temp"] if channels.get("temp") is not None and np.asarray(channels["temp"]).size else [],
        "motion": ["acc"] if channels.get("acc") is not None and np.asarray(channels["acc"]).size else [],
    }

    for name, keys in groups.items():
        if keys:
            present.extend(keys)
        else:
            missing.append(name)

    if duration is None:
        available = [np.asarray(channels[k]).shape[0] for k in present if np.asarray(channels[k]).size]
        if available:
            primary = max(available)
            duration = primary / max(_fs_for(fs, "eda" if "eda" in present else present[0]), 1.0)

    if duration is not None and duration < 20:
        score -= 45
        issues.append(
            {
                "code": "short_recording",
                "severity": "critical",
                "message": f"Recording is {duration:.0f}s long; at least 20s is required for a stable estimate.",
            }
        )

    if not groups["cardiac"]:
        score -= 20
        issues.append(
            {
                "code": "missing_cardiac",
                "severity": "high",
                "message": "No ECG, BVP or heart-rate channel found; cardiac features are imputed.",
            }
        )
    if not groups["eda"]:
        score -= 12
        issues.append(
            {
                "code": "missing_eda",
                "severity": "medium",
                "message": "No electrodermal channel found; EDA features are imputed.",
            }
        )
    if require_raw_channels and not (groups["cardiac"] or groups["eda"]):
        issues.append(
            {
                "code": "insufficient_channels",
                "severity": "critical",
                "message": "Neither cardiac nor electrodermal signals are present, so no reliable pattern can be estimated.",
            }
        )

    for key in present:
        values = np.asarray(channels[key])
        miss = _missing_fraction(values.ravel() if values.ndim == 1 else values[:, 0])
        if miss > 0.5:
            score -= 25
            issues.append(
                {
                    "code": f"missing_values_{key}",
                    "severity": "critical",
                    "message": f"{CHANNEL_LABELS.get(key, key)} is more than half missing.",
                }
            )
        elif miss > 0.15:
            score -= 10
            issues.append(
                {
                    "code": f"gaps_{key}",
                    "severity": "medium",
                    "message": f"{CHANNEL_LABELS.get(key, key)} contains about {miss * 100:.0f}% gaps.",
                }
            )
        arr = clean_array(values)
        if arr.size and _flat(arr):
            score -= 18
            issues.append(
                {
                    "code": f"flat_{key}",
                    "severity": "high",
                    "message": f"{CHANNEL_LABELS.get(key, key)} is flat or disconnected.",
                }
            )
        if arr.size > 8 and key in {"ecg", "bvp"}:
            channel_fs = _fs_for(fs, key)
            ratio = _noise_ratio(arr, channel_fs)
            if ratio > 1.1:
                penalty = 24 if ratio > 2.0 else 14
                score -= penalty
                issues.append(
                    {
                        "code": f"noisy_{key}",
                        "severity": "high" if ratio > 2.0 else "medium",
                        "message": (
                            f"{CHANNEL_LABELS.get(key, key)} shows substantial high-frequency noise or motion "
                            "artefact, which can distort beat detection."
                        ),
                    }
                )
            if key == "ecg" and channel_fs > 20:
                beats = detect_beats(arr, channel_fs)
                if beats.size >= 4:
                    rr = np.diff(beats) / channel_fs
                    rr = rr[(rr > 0.2) & (rr < 3.0)]
                    if rr.size >= 3:
                        heart_rate = 60.0 / float(np.median(rr))
                        rr_cv = float(np.std(rr) / (np.mean(rr) + 1e-9))
                        if heart_rate < 35 or heart_rate > 190:
                            score -= 20
                            issues.append(
                                {
                                    "code": "implausible_cardiac",
                                    "severity": "high",
                                    "message": (
                                        f"Detected heart rate ({heart_rate:.0f} bpm) is outside a plausible range; "
                                        "beat detection may have locked onto noise."
                                    ),
                                }
                            )
                        elif rr_cv > 0.35:
                            score -= 14
                            issues.append(
                                {
                                    "code": "irregular_cardiac",
                                    "severity": "medium",
                                    "message": (
                                        "Beat-to-beat intervals are highly irregular, which often indicates artefact "
                                        "rather than physiology in short recordings."
                                    ),
                                }
                            )
        if key == "eda" and arr.size:
            mean = float(np.mean(arr))
            if mean < 0 or mean > 60:
                score -= 10
                issues.append(
                    {
                        "code": "implausible_eda",
                        "severity": "high",
                        "message": "Skin conductance values are outside a plausible range (0–60 µS).",
                    }
                )
        if key == "temp" and arr.size:
            mean = float(np.mean(arr))
            if not 20 <= mean <= 45:
                score -= 8
                issues.append(
                    {
                        "code": "implausible_temp",
                        "severity": "medium",
                        "message": "Skin temperature is outside a plausible range (20–45 °C).",
                    }
                )

    score = float(max(0.0, min(100.0, score)))
    if score >= 80:
        grade = "good"
    elif score >= 60:
        grade = "fair"
    elif score >= 40:
        grade = "poor"
    else:
        grade = "insufficient"

    return {
        "score": round(score, 1),
        "grade": grade,
        "issues": issues,
        "channels": present,
        "missing_channels": missing,
        "duration_seconds": round(float(duration or 0), 1),
    }


# --------------------------------------------------------------------------- #
# CSV ingestion
# --------------------------------------------------------------------------- #
ALIASES: dict[str, set[str]] = {
    "ecg": {"ecg", "ekg", "ecgsignal", "chestecg", "ecgmv"},
    "bvp": {"bvp", "ppg", "bloodvolumepulse", "pulsewave"},
    "eda": {"eda", "gsr", "scl", "electrodermal", "electrodermalactivity", "skinconductance"},
    "resp": {"resp", "respiration", "rsp", "breathing", "respirationamplitude"},
    "temp": {"temp", "temperature", "skintemp", "bodytemp", "skintemperature"},
    "emg": {"emg", "muscleactivity"},
    "hr": {"hr", "heartrate", "heartratebpm", "pulse", "hrbpm"},
}
ACC_ALIASES = {
    "x": {"accx", "accelx", "accelerationx", "xaxis", "acc_x"},
    "y": {"accy", "accely", "accelerationy", "yaxis", "acc_y"},
    "z": {"accz", "accelz", "accelerationz", "zaxis", "acc_z"},
}
TIME_ALIASES = {
    "time",
    "timestamp",
    "t",
    "seconds",
    "sec",
    "elapsed",
    "elapsedtime",
    "times",
    "timeseconds",
    "timeinseconds",
    "elapsedseconds",
}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def detect_channels(df) -> dict[str, Any]:
    """Map generic CSV headers onto physiological channels."""
    normalized = {_norm(c): c for c in df.columns}
    out: dict[str, Any] = {}
    column_map: dict[str, str] = {}

    for channel, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                out[channel] = df[normalized[alias]].to_numpy(dtype=float)
                column_map[channel] = normalized[alias]
                break

    acc_cols = {}
    for axis, aliases in ACC_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                acc_cols[axis] = normalized[alias]
                break
    if {"x", "y", "z"} <= acc_cols.keys():
        out["acc"] = np.column_stack(
            [df[acc_cols[a]].to_numpy(dtype=float) for a in ("x", "y", "z")]
        )
        column_map["acc"] = f"{acc_cols['x']},{acc_cols['y']},{acc_cols['z']}"

    return {"channels": out, "columns": column_map, "time_column": next((v for k, v in normalized.items() if k in TIME_ALIASES), None)}


def infer_fs(df, fs_hint: float | None, time_column: str | None) -> tuple[float, str]:
    if time_column and time_column in df.columns:
        t = df[time_column].to_numpy(dtype=float)
        t = t[np.isfinite(t)]
        if t.size > 2:
            dt = np.diff(t)
            dt = dt[dt > 0]
            if dt.size:
                median_dt = float(np.median(dt))
                if median_dt > 0:
                    fs = 1.0 / median_dt
                    if fs >= 0.5:
                        return float(round(fs, 3)), f"time column ({time_column})"
    if fs_hint and fs_hint > 0:
        return float(fs_hint), "user supplied"
    return 64.0, "default assumption"


def features_from_frame(
    df,
    fs_hint: float | None = None,
    window_seconds: float = 60.0,
    step_seconds: float = 30.0,
) -> dict[str, Any]:
    """Validate a CSV frame, window it, and extract features per window."""
    detected = detect_channels(df)
    channels = {k: v for k, v in detected["channels"].items() if np.asarray(v).size}
    if not channels:
        raise ValueError(
            "No recognised physiological columns were found. Expected names such as ECG, BVP, EDA, Resp, Temp, EMG or ACC_x/ACC_y/ACC_z."
        )

    fs, fs_source = infer_fs(df, fs_hint, detected["time_column"])
    n_samples = max(np.asarray(v).shape[0] for v in channels.values())
    duration = n_samples / fs if fs > 0 else 0.0

    window_samples = max(8, int(window_seconds * fs))
    step_samples = max(4, int(step_seconds * fs))
    starts = list(range(0, max(1, n_samples - window_samples + 1), step_samples)) or [0]

    windows: list[dict[str, Any]] = []
    for start in starts:
        end = min(n_samples, start + window_samples)
        if end - start < 8:
            continue
        sliced = {}
        for key, values in channels.items():
            arr = np.asarray(values)
            sliced[key] = arr[start:end] if arr.ndim > 1 else arr[start:end]
        win_duration = (end - start) / fs
        feats = extract_window_features(sliced, fs, win_duration)
        quality = assess_quality(sliced, fs, win_duration)
        windows.append(
            {
                "start_seconds": round(start / fs, 2),
                "end_seconds": round(end / fs, 2),
                "duration_seconds": round(win_duration, 2),
                "features": feats,
                "quality": quality,
            }
        )

    if not windows:
        raise ValueError("The file is too short to form a signal window.")

    overall = assess_quality(channels, fs, duration)
    preview = {}
    for key, values in channels.items():
        arr = np.asarray(values)
        if arr.ndim > 1:
            preview[key] = arr[:, 0]
        else:
            preview[key] = arr

    coverage = {
        "missing_values": {
            key: round(
                float(np.mean(~np.isfinite(np.asarray(vals, dtype=float))) * 100.0), 2
            )
            for key, vals in channels.items()
        },
        "non_finite_total": int(
            sum(int(np.sum(~np.isfinite(np.asarray(vals, dtype=float)))) for vals in channels.values())
        ),
    }

    return {
        "channels": channels,
        "channel_columns": detected["columns"],
        "sampling_rate": fs,
        "sampling_rate_source": fs_source,
        "duration_seconds": duration,
        "n_samples": n_samples,
        "windows": windows,
        "quality": overall,
        "coverage": coverage,
        "preview": preview,
    }
