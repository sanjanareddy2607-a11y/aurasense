"""Deterministic simulated physiological signals.

Nothing here is a measurement.  The simulator produces synthetic ECG,
electrodermal, respiratory, temperature and accelerometer channels so the live
monitor can exercise the *real* preprocessing and inference pipeline without
hardware.  Every response carries ``is_simulation`` and the UI labels it.
"""
from __future__ import annotations

from typing import Any

import numpy as np

FS = 250.0  # synthetic ECG sampling rate

SCENARIOS: dict[str, dict[str, Any]] = {
    "resting": {
        "label": "Resting / neutral",
        "description": "Slow, regular cardiac rhythm with low electrodermal activity and steady breathing.",
        "hr": 62.0,
        "sinus_amp_s": 0.055,
        "eda_base": 2.4,
        "eda_range": 0.35,
        "scr_rate": 2.0,
        "resp_rate": 13.5,
        "motion": 0.02,
        "noise": 0.012,
        "dropout": 0.0,
        "expected_pattern": "neutral-associated",
    },
    "arousal": {
        "label": "Increased physiological arousal",
        "description": "Elevated heart rate with reduced beat-to-beat variability and rising skin conductance.",
        "hr": 92.0,
        "sinus_amp_s": 0.018,
        "eda_base": 6.6,
        "eda_range": 2.4,
        "scr_rate": 9.0,
        "resp_rate": 19.0,
        "motion": 0.035,
        "noise": 0.02,
        "dropout": 0.0,
        "expected_pattern": "stress-associated",
    },
    "activity": {
        "label": "Movement / activity",
        "description": "High movement intensity and elevated heart rate — a confound that can mimic arousal.",
        "hr": 112.0,
        "sinus_amp_s": 0.02,
        "eda_base": 4.4,
        "eda_range": 1.6,
        "scr_rate": 5.0,
        "resp_rate": 23.0,
        "motion": 0.42,
        "noise": 0.035,
        "dropout": 0.0,
        "expected_pattern": "ambiguous (movement artefact)",
    },
    "noisy": {
        "label": "Poor contact / noisy signal",
        "description": "Disconnected EDA and motion-corrupted ECG intended to trigger an insufficient-quality result.",
        "hr": 78.0,
        "sinus_amp_s": 0.03,
        "eda_base": 0.0,
        "eda_range": 0.0,
        "scr_rate": 0.0,
        "resp_rate": 16.0,
        "motion": 0.55,
        "noise": 0.42,
        "dropout": 0.28,
        "expected_pattern": "insufficient signal quality",
    },
    "recovery": {
        "label": "Recovery after arousal",
        "description": "A gradual return toward resting heart rate and skin conductance after a simulated arousal episode.",
        "hr": 88.0,
        "sinus_amp_s": 0.035,
        "eda_base": 5.1,
        "eda_range": 1.2,
        "scr_rate": 5.0,
        "resp_rate": 17.0,
        "motion": 0.03,
        "noise": 0.018,
        "dropout": 0.0,
        "expected_pattern": "transitional",
    },
}


def _gaussian_pulse(signal: np.ndarray, fs: float, center: float, amplitude: float, sigma: float) -> None:
    start = int((center - 4 * sigma) * fs)
    end = int((center + 4 * sigma) * fs)
    start = max(start, 0)
    end = min(end, signal.size)
    if start >= end:
        return
    t = np.arange(start, end) / fs
    signal[start:end] += amplitude * np.exp(-0.5 * ((t - center) / sigma) ** 2)


def _ecg(t0: float, seconds: int, profile: dict[str, Any], rng: np.random.Generator, fs: float = FS) -> np.ndarray:
    """Synthesise an ECG-like trace for the absolute interval [t0, t0+seconds)."""
    n = int(seconds * fs)
    t = np.arange(n) / fs
    signal = np.zeros(n)
    mean_rr = 60.0 / profile["hr"]
    # Approximate the beat index at the start of this window so successive
    # windows line up in time.
    beat = max(0, int(t0 / mean_rr) - 1)
    beat_time = beat * mean_rr
    while beat_time < t0 + seconds:
        if beat_time >= t0 - 0.5:
            local = beat_time - t0
            _gaussian_pulse(signal, fs, local - 0.16, 0.08, 0.018)   # P
            _gaussian_pulse(signal, fs, local - 0.02, -0.12, 0.008)  # Q
            _gaussian_pulse(signal, fs, local, 1.0, 0.006)           # R
            _gaussian_pulse(signal, fs, local + 0.022, -0.16, 0.009)  # S
            _gaussian_pulse(signal, fs, local + 0.24, 0.16, 0.055)   # T
        respiratory = profile["sinus_amp_s"] * np.sin(2 * np.pi * (profile["resp_rate"] / 60.0) * beat_time)
        beat_rr = mean_rr * (1.0 + respiratory) + rng.normal(0, 0.006)
        beat_rr = float(np.clip(beat_rr, 0.35, 1.6))
        beat_time += beat_rr
        beat += 1

    time = t0 + t
    signal += 0.035 * np.sin(2 * np.pi * 0.18 * time)  # baseline wander
    signal += rng.normal(0, profile["noise"], n)
    if profile["motion"] > 0.2:
        signal += rng.normal(0, profile["motion"] * 0.35, n) * (np.sin(2 * np.pi * 0.9 * time) > 0.2)
    if profile["dropout"] > 0:
        dropout = rng.random(n) < profile["dropout"] * 0.06
        signal[dropout] = np.nan
    return signal


def _eda(t0: float, seconds: int, profile: dict[str, Any], rng: np.random.Generator, fs: float = 4.0) -> np.ndarray:
    n = int(seconds * fs)
    t = t0 + np.arange(n) / fs
    base = profile["eda_base"] + 0.35 * np.sin(2 * np.pi * 0.004 * t + 0.4)
    signal = base + rng.normal(0, 0.02, n)
    if profile["eda_range"] > 0:
        rate_per_min = profile["scr_rate"]
        expected = max(1, int(rate_per_min / 60.0 * seconds * 1.4))
        onsets = t0 + np.sort(rng.uniform(0, seconds, expected))
        for onset in onsets:
            idx = np.where((t >= onset) & (t < onset + 8))[0]
            if idx.size:
                dt = t[idx] - onset
                response = profile["eda_range"] * 0.28 * (np.exp(-dt / 3.0) - np.exp(-dt / 0.7))
                signal[idx] += response
    if profile["dropout"] > 0:
        signal[rng.random(n) < profile["dropout"]] = np.nan
    return signal


def _resp(t0: float, seconds: int, profile: dict[str, Any], rng: np.random.Generator, fs: float = 4.0) -> np.ndarray:
    n = int(seconds * fs)
    t = t0 + np.arange(n) / fs
    rate = profile["resp_rate"] / 60.0
    signal = np.sin(2 * np.pi * rate * t) + 0.18 * np.sin(2 * np.pi * rate * 2.1 * t + 1.1)
    signal += rng.normal(0, 0.035, n)
    if profile["dropout"] > 0:
        signal[rng.random(n) < profile["dropout"] * 0.5] = np.nan
    return signal


def _temp(t0: float, seconds: int, profile: dict[str, Any], rng: np.random.Generator, fs: float = 4.0) -> np.ndarray:
    n = int(seconds * fs)
    t = t0 + np.arange(n) / fs
    drift = -0.00035 * profile["hr"] / 60.0 * t
    return 33.4 + drift + rng.normal(0, 0.004, n)


def _acc(t0: float, seconds: int, profile: dict[str, Any], rng: np.random.Generator, fs: float = 4.0) -> np.ndarray:
    n = int(seconds * fs)
    t = t0 + np.arange(n) / fs
    motion = profile["motion"]
    base = np.stack(
        [
            0.02 * np.sin(2 * np.pi * 0.4 * t),
            0.02 * np.cos(2 * np.pi * 0.3 * t),
            np.ones(n),
        ],
        axis=1,
    )
    noise = rng.normal(0, max(motion, 0.005), (n, 3))
    return base + noise


def generate_window(scenario: str, t0: float, seconds: int, seed: int = 0) -> dict[str, Any]:
    """Generate one deterministic multi-channel window starting at ``t0`` seconds."""
    profile = SCENARIOS.get(scenario) or SCENARIOS["resting"]
    rng = np.random.default_rng((seed * 7919 + int(t0 * 4) + 17) & 0xFFFFFFFF)
    return {
        "scenario": scenario,
        "profile": profile,
        "t0": float(t0),
        "seconds": float(seconds),
        "channels": {
            "ecg": _ecg(t0, seconds, profile, rng, FS),
            "eda": _eda(t0, seconds, profile, rng, 4.0),
            "resp": _resp(t0, seconds, profile, rng, 4.0),
            "temp": _temp(t0, seconds, profile, rng, 4.0),
            "acc": _acc(t0, seconds, profile, rng, 4.0),
        },
        "sampling_rates": {"ecg": FS, "eda": 4.0, "resp": 4.0, "temp": 4.0, "acc": 4.0},
    }


def display_payload(window: dict[str, Any]) -> dict[str, Any]:
    """Downsample channels for chart rendering."""
    channels = window["channels"]
    ecg = channels["ecg"]
    # Last 8 seconds of ECG, decimated to ~220 points.
    tail = int(8 * FS)
    ecg_tail = ecg[-tail:]
    step = max(1, ecg_tail.size // 220)
    ecg_points = [None if not np.isfinite(v) else round(float(v), 4) for v in ecg_tail[::step]]
    eda = channels["eda"]
    resp = channels["resp"]
    acc = channels["acc"]
    magnitude = np.sqrt(np.sum(acc**2, axis=1)) if np.asarray(acc).ndim == 2 else np.abs(acc)
    return {
        "ecg": ecg_points,
        "eda": [None if not np.isfinite(v) else round(float(v), 4) for v in eda],
        "resp": [None if not np.isfinite(v) else round(float(v), 4) for v in resp[-int(30 * 4):]],
        "motion": [round(float(v), 4) for v in magnitude[-int(30 * 4):]],
        "ecg_sampling_rate": round(FS / step, 2),
        "channels": ["ecg", "eda", "resp", "acc"],
    }


def window_seconds(elapsed: float, desired: int = 60) -> float:
    return float(min(max(elapsed, 0.0), desired))
