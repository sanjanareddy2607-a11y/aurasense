"""Train and evaluate AuraSense stress-pattern models on WESAD.

Evaluation is participant-independent: every window from a held-out
participant is predicted by a model that never saw that participant, using
GroupKFold on the participant identifier.  No random window-level splits are
used anywhere.

Run from ``app/backend``:
    .venv/Scripts/python -m ml.train
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from ml.features import FEATURE_NAMES

BACKEND_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS = BACKEND_DIR / "ml" / "artifacts"
LABEL_ORDER = ["neutral", "stress", "amusement"]
RANDOM_STATE = 42


def _xgb_available() -> bool:
    try:
        import xgboost  # noqa: F401

        return True
    except Exception:
        return False


def build_models() -> dict[str, object]:
    models: dict[str, object] = {
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "Support Vector Machine": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("svc", SVC(C=2.0, gamma="scale", kernel="rbf", probability=True, class_weight="balanced", random_state=RANDOM_STATE)),
            ]
        ),
    }
    if _xgb_available():
        from xgboost import XGBClassifier

        models["XGBoost"] = XGBClassifier(
            n_estimators=350,
            max_depth=5,
            learning_rate=0.06,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
    else:
        models["Gradient Boosting"] = HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.08,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )
    return models


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, labels: list[int]) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    per_class = {}
    for idx, name in enumerate(LABEL_ORDER):
        tp = int(cm[idx, idx])
        support = int(cm[idx, :].sum())
        predicted = int(cm[:, idx].sum())
        per_class[name] = {
            "precision": round(float(tp / predicted), 4) if predicted else 0.0,
            "recall": round(float(tp / support), 4) if support else 0.0,
            "f1": round(float(2 * tp / (predicted + support)), 4) if (predicted + support) else 0.0,
            "support": support,
        }
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(precision_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        "confusion_matrix": cm.tolist(),
        "per_class": per_class,
        "n_test_windows": int(len(y_true)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default=str(ARTIFACTS / "wesad_features.csv"))
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    features_path = Path(args.features)
    if not features_path.exists():
        raise SystemExit(
            f"Feature table not found at {features_path}. Run `python -m ml.wesad_extract` first."
        )

    data = pd.read_csv(features_path)
    data = data.dropna(subset=["label", "subject"])
    available = [f for f in FEATURE_NAMES if f in data.columns]
    missing_columns = [f for f in FEATURE_NAMES if f not in data.columns]
    if missing_columns:
        raise SystemExit(f"Feature columns missing from training data: {missing_columns}")

    X = data[available].to_numpy(dtype=float)
    y = data["label"].to_numpy()
    groups = data["subject"].to_numpy()
    codes = {name: i for i, name in enumerate(LABEL_ORDER)}
    y_encoded = np.array([codes[label] for label in y], dtype=int)
    label_ids = list(range(len(LABEL_ORDER)))

    n_splits = min(args.folds, len(np.unique(groups)))
    splitter = GroupKFold(n_splits=n_splits)
    folds = list(splitter.split(X, y_encoded, groups))
    print(f"{len(X)} windows | {len(np.unique(groups))} participants | {n_splits}-fold GroupKFold", flush=True)

    results = []
    per_subject: dict[str, dict[str, float]] = {}
    best_name = ""
    best_score = -1.0
    best_oof = None

    for name, model in build_models().items():
        oof_pred = np.full(len(y_encoded), -1, dtype=int)
        oof_proba = np.zeros((len(y_encoded), len(LABEL_ORDER)))
        fold_metrics = []
        for fold_idx, (train_idx, test_idx) in enumerate(folds):
            model.fit(X[train_idx], y_encoded[train_idx])
            pred = model.predict(X[test_idx])
            proba = model.predict_proba(X[test_idx])
            oof_pred[test_idx] = pred
            oof_proba[test_idx] = proba
            fold_metrics.append(_metrics(y_encoded[test_idx], pred, label_ids))
            print(f"  {name} fold {fold_idx + 1}/{n_splits} done", flush=True)

        overall = _metrics(y_encoded, oof_pred, label_ids)
        overall["fold_balanced_accuracy"] = [
            round(float(f["balanced_accuracy"]), 4) for f in fold_metrics
        ]
        overall["fold_accuracy"] = [round(float(f["accuracy"]), 4) for f in fold_metrics]
        overall["balanced_accuracy_std"] = round(float(np.std(overall["fold_balanced_accuracy"])), 4)

        subject_scores = {}
        for subject in sorted(np.unique(groups)):
            mask = groups == subject
            if mask.sum() < 5:
                continue
            subject_scores[subject] = {
                "accuracy": round(float(accuracy_score(y_encoded[mask], oof_pred[mask])), 4),
                "balanced_accuracy": round(float(balanced_accuracy_score(y_encoded[mask], oof_pred[mask])), 4),
                "windows": int(mask.sum()),
            }
        per_subject[name] = subject_scores

        results.append(
            {
                "model": name,
                "metrics": overall,
                "per_subject": subject_scores,
                "mean_subject_balanced_accuracy": round(
                    float(np.mean([v["balanced_accuracy"] for v in subject_scores.values()])), 4
                )
                if subject_scores
                else 0.0,
            }
        )
        print(
            f"{name}: balanced accuracy {overall['balanced_accuracy']:.3f} | macro F1 {overall['f1_macro']:.3f}",
            flush=True,
        )
        if overall["balanced_accuracy"] > best_score:
            best_score = float(overall["balanced_accuracy"])
            best_name = name
            best_oof = (oof_pred.copy(), oof_proba.copy())

    # Global feature importance for the selected model: permutation importance
    # averaged across the same participant-independent folds.
    best_model_proto = build_models()[best_name]
    importance_rows = []
    for train_idx, test_idx in folds:
        best_model_proto.fit(X[train_idx], y_encoded[train_idx])
        result = permutation_importance(
            best_model_proto,
            X[test_idx],
            y_encoded[test_idx],
            n_repeats=8,
            random_state=RANDOM_STATE,
            scoring="balanced_accuracy",
            n_jobs=-1,
        )
        importance_rows.append(result.importances_mean)
    importance = np.mean(np.vstack(importance_rows), axis=0)
    importance = np.clip(importance, 0, None)
    total = float(importance.sum()) or 1.0
    feature_importance = [
        {"feature": feature, "importance": round(float(value), 5), "share": round(float(value / total), 4)}
        for feature, value in sorted(zip(available, importance), key=lambda p: p[1], reverse=True)
    ]

    # Final model trained on all participants for inference.
    final_model = build_models()[best_name]
    final_model.fit(X, y_encoded)

    imputer = SimpleImputer(strategy="median").fit(X)
    impute_values = {
        feature: round(float(value), 6) for feature, value in zip(available, imputer.statistics_)
    }
    reference = {
        feature: {
            "p10": round(float(np.nanpercentile(X[:, i], 10)), 4),
            "p50": round(float(np.nanpercentile(X[:, i], 50)), 4),
            "p90": round(float(np.nanpercentile(X[:, i], 90)), 4),
            "mean": round(float(np.nanmean(X[:, i])), 4),
            "std": round(float(np.nanstd(X[:, i])), 4),
        }
        for i, feature in enumerate(available)
    }

    version_seed = f"{best_name}-{len(X)}-{hashlib.sha1(np.round(X[:, :3], 3).tobytes()).hexdigest()[:8]}"
    version = f"aura-wesad-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{version_seed[-6:]}"

    dataset_summary_path = ARTIFACTS / "dataset_summary.json"
    dataset_summary = (
        json.loads(dataset_summary_path.read_text(encoding="utf-8"))
        if dataset_summary_path.exists()
        else {}
    )

    artifact = {
        "model": final_model,
        "model_name": best_name,
        "model_version": version,
        "feature_names": available,
        "classes": LABEL_ORDER,
        "impute_values": impute_values,
        "reference": reference,
        "feature_importance": feature_importance,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_windows": int(len(X)),
        "participants": sorted(np.unique(groups).tolist()),
        "cv_strategy": f"{n_splits}-fold GroupKFold by participant",
        "label_mapping": {str(k): v for k, v in codes.items()},
        "global_metrics": next(r["metrics"] for r in results if r["model"] == best_name),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, ARTIFACTS / "model.joblib")

    evaluation = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "WESAD (Schmidt & Reiss, 2018)",
        "dataset_citation": "Schmidt, P., & Reiss, A. (2018). WESAD. DOI: 10.24432/C57K5T",
        "evaluation_strategy": f"{n_splits}-fold GroupKFold grouped by participant (no window leakage)",
        "windows": int(len(X)),
        "participants": int(len(np.unique(groups))),
        "class_distribution": {k: int(v) for k, v in pd.Series(y).value_counts().to_dict().items()},
        "classes": LABEL_ORDER,
        "models": results,
        "best_model": best_name,
        "best_model_version": version,
        "feature_importance": feature_importance,
        "per_subject": per_subject,
        "confusion_matrices": {r["model"]: r["metrics"]["confusion_matrix"] for r in results},
        "dataset_summary": dataset_summary,
        "limitations": [
            "WESAD contains 15 participants recorded in a laboratory with a specific stress protocol (Trier Social Stress Test), so generalisation to everyday settings is not established.",
            "Window-level features are correlated within a participant; participant-independent folds remove identity leakage but not within-condition similarity.",
            "Skin-conductance tonic/phasic separation uses a moving-average estimate rather than a full deconvolution model.",
            "Feature importance describes model behaviour, not the biological cause of a physiological change.",
        ],
    }
    (ARTIFACTS / "metrics.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")
    print(f"Saved model {version} and metrics to {ARTIFACTS}", flush=True)


if __name__ == "__main__":
    main()
