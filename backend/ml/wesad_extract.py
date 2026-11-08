"""WESAD extraction: participant pickles -> windowed feature table.

WESAD (Schmidt & Reiss, 2018) archives one pickle per participant containing
chest signals at 700 Hz, wrist signals (BVP 64 Hz, EDA/TEMP 4 Hz, ACC 32 Hz)
and a label array at 700 Hz.  Labels used here: 1 = baseline/neutral,
2 = stress, 3 = amusement.  Unlabelled/transition segments and meditation are
excluded.

Run from ``app/backend``:
    .venv/Scripts/python -m ml.wesad_extract --subjects S2 S3 ...
Feature tables are cached under ``ml/artifacts/features``.
"""
from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features import (
    WESAD_LABEL_NAMES,
    assess_quality,
    extract_window_features,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_WESAD = BACKEND_DIR.parent.parent / "WESAD"
ARTIFACTS = BACKEND_DIR / "ml" / "artifacts"
CACHE = ARTIFACTS / "features"

WINDOW_SECONDS = 60.0
STEP_SECONDS = 30.0
CHEST_FS = 700.0
WRIST_FS = {"bvp": 64.0, "eda": 4.0, "temp": 4.0, "acc": 32.0}


def discover_subjects(wesad_dir: Path) -> list[str]:
    subjects = []
    for path in sorted(wesad_dir.glob("S*")):
        if path.is_dir() and (path / f"{path.name}.pkl").exists():
            subjects.append(path.name)
    return sorted(subjects, key=lambda s: int(s[1:]) if s[1:].isdigit() else s)


def _load_subject(path: Path) -> dict:
    with open(path, "rb") as handle:
        return pickle.load(handle, encoding="latin1")


def _window_label(labels: np.ndarray, start: int, end: int) -> tuple[int, float, dict[int, int]]:
    segment = labels[start:end]
    if segment.size == 0:
        return 0, 0.0, {}
    values, counts = np.unique(segment, return_counts=True)
    mapping = {int(v): int(c) for v, c in zip(values, counts)}
    idx = int(np.argmax(counts))
    majority = int(values[idx])
    coverage = float(counts[idx] / segment.size)
    return majority, coverage, mapping


def extract_subject(wesad_dir: Path, subject: str, force: bool = False) -> Path:
    cache_path = CACHE / f"{subject}_features.csv"
    if cache_path.exists() and not force:
        return cache_path

    raw = _load_subject(wesad_dir / subject / f"{subject}.pkl")
    chest = raw["signal"]["chest"]
    wrist = raw["signal"]["wrist"]
    labels = np.asarray(raw["label"]).ravel()
    n = labels.size
    window = int(WINDOW_SECONDS * CHEST_FS)
    step = int(STEP_SECONDS * CHEST_FS)

    wrist_index = {
        "bvp": (np.arange(wrist["BVP"].shape[0]) / WRIST_FS["bvp"] * CHEST_FS).astype(int),
        "eda": (np.arange(wrist["EDA"].shape[0]) / WRIST_FS["eda"] * CHEST_FS).astype(int),
        "temp": (np.arange(wrist["TEMP"].shape[0]) / WRIST_FS["temp"] * CHEST_FS).astype(int),
        "acc": (np.arange(wrist["ACC"].shape[0]) / WRIST_FS["acc"] * CHEST_FS).astype(int),
    }

    rows: list[dict] = []
    for start in range(0, max(1, n - window + 1), step):
        end = min(n, start + window)
        majority, coverage, counts = _window_label(labels, start, end)
        if majority not in WESAD_LABEL_NAMES or coverage < 0.9:
            continue

        chest_slice = {
            "ecg": chest["ECG"][start:end, 0],
            "eda": chest["EDA"][start:end, 0],
            "resp": chest["Resp"][start:end, 0],
            "temp": chest["Temp"][start:end, 0],
            "emg": chest["EMG"][start:end, 0],
            "acc": chest["ACC"][start:end, :],
        }
        quality = assess_quality(chest_slice, CHEST_FS, (end - start) / CHEST_FS)

        wrist_slice = {}
        for key in ("bvp", "eda", "temp", "acc"):
            idx = wrist_index[key]
            mask = (idx >= start) & (idx < end)
            if mask.any():
                wrist_slice[key] = wrist[{"bvp": "BVP", "eda": "EDA", "temp": "TEMP", "acc": "ACC"}[key]][mask]

        features = extract_window_features(chest_slice, CHEST_FS, (end - start) / CHEST_FS)

        rows.append(
            {
                "subject": subject,
                "start_seconds": round(start / CHEST_FS, 2),
                "end_seconds": round(end / CHEST_FS, 2),
                "label_id": majority,
                "label": WESAD_LABEL_NAMES[majority],
                "label_coverage": round(coverage, 3),
                "quality_score": quality["score"],
                "quality_grade": quality["grade"],
                **features,
            }
        )

    frame = pd.DataFrame(rows)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    print(f"[{time.strftime('%H:%M:%S')}] {subject}: {len(rows)} windows -> {cache_path.name}", flush=True)
    return cache_path


def build_dataset(subjects: list[str], force: bool = False) -> dict:
    frames = []
    for subject in subjects:
        path = extract_subject(DEFAULT_WESAD, subject, force=force)
        frame = pd.read_csv(path)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)

    summary = {
        "participants": sorted(data["subject"].unique().tolist()),
        "participant_count": int(data["subject"].nunique()),
        "windows": int(len(data)),
        "class_distribution": {
            k: int(v) for k, v in data["label"].value_counts().to_dict().items()
        },
        "class_distribution_by_subject": {
            subj: {k: int(v) for k, v in grp["label"].value_counts().to_dict().items()}
            for subj, grp in data.groupby("subject")
        },
        "channels": {
            "chest": ["ECG", "EDA", "EMG", "Resp", "Temp", "ACC (x,y,z)"],
            "wrist": ["BVP", "EDA", "TEMP", "ACC (x,y,z)"],
        },
        "sampling_rates": {
            "chest_hz": 700,
            "wrist_bvp_hz": 64,
            "wrist_eda_hz": 4,
            "wrist_temp_hz": 4,
            "wrist_acc_hz": 32,
        },
        "window_seconds": WINDOW_SECONDS,
        "step_seconds": STEP_SECONDS,
        "label_mapping": {"1": "neutral", "2": "stress", "3": "amusement"},
        "excluded_labels": "not defined (0), meditation (4), transitions with <90% label coverage",
        "missing_feature_percent": {
            col: round(float(data[col].isna().mean() * 100.0), 2)
            for col in data.columns
            if data[col].dtype.kind in "fi"
        },
    }
    (ARTIFACTS / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    data.to_csv(ARTIFACTS / "wesad_features.csv", index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract WESAD window features")
    parser.add_argument("--subjects", nargs="*", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    subjects = args.subjects or discover_subjects(DEFAULT_WESAD)
    if not subjects:
        raise SystemExit(f"No WESAD participant folders found in {DEFAULT_WESAD}")
    print(f"Extracting {len(subjects)} participants from {DEFAULT_WESAD}", flush=True)
    summary = build_dataset(subjects, force=args.force)
    print(json.dumps({k: summary[k] for k in ("participant_count", "windows", "class_distribution")}, indent=2))


if __name__ == "__main__":
    main()
