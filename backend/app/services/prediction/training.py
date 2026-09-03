"""Train, evaluate, and persist recovery and churn models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.core.config import get_settings
from app.services.data.loaders import load_directory
from app.services.features.constants import (
    CHURN_CATEGORICAL_FEATURES,
    CHURN_FEATURE_COLUMNS,
    CHURN_NUMERIC_FEATURES,
    LEAKAGE_COLUMNS,
    RECOVERY_CATEGORICAL_FEATURES,
    RECOVERY_FEATURE_COLUMNS,
    RECOVERY_NUMERIC_FEATURES,
)
from app.services.features.dataset import build_churn_training_set, build_recovery_training_set
from app.services.features.preprocess import build_preprocessor

MODEL_VERSION = "0.1.0"


def _assert_no_leakage(columns: list[str]) -> None:
    leaked = [name for name in columns if name in LEAKAGE_COLUMNS]
    if leaked:
        raise ValueError(f"Leakage columns present in features: {leaked}")


def _metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, Any]:
    y_pred = (y_prob >= 0.5).astype(int)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "positive_rate": float(np.mean(y_true)),
        "n_samples": int(len(y_true)),
    }


def _candidate_models(random_state: int) -> dict[str, Any]:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=random_state,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=160,
            max_depth=6,
            min_samples_leaf=15,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        ),
    }


def _fit_and_compare(
    X: pd.DataFrame,
    y: pd.Series,
    numeric: tuple[str, ...],
    categorical: tuple[str, ...],
    random_state: int,
) -> dict[str, Any]:
    _assert_no_leakage(list(X.columns))
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_state,
        stratify=y,
    )
    compared: dict[str, dict[str, Any]] = {}
    fitted: dict[str, Pipeline] = {}
    for name, estimator in _candidate_models(random_state).items():
        pipeline = Pipeline(
            steps=[
                ("preprocess", build_preprocessor(numeric, categorical)),
                ("model", estimator),
            ]
        )
        pipeline.fit(X_train, y_train)
        proba = pipeline.predict_proba(X_test)[:, 1]
        compared[name] = _metrics(y_test.to_numpy(), proba)
        fitted[name] = pipeline

    selected = max(compared.items(), key=lambda item: item[1]["roc_auc"])[0]
    lr_auc = compared["logistic_regression"]["roc_auc"]
    rf_auc = compared["random_forest"]["roc_auc"]
    # Prefer the simpler model when the tree gain is negligible.
    if selected == "random_forest" and rf_auc < lr_auc + 0.01:
        selected = "logistic_regression"

    winner = fitted[selected]
    winner.fit(X, y)
    leakage_warning = compared[selected]["roc_auc"] >= 0.97
    return {
        "pipeline": winner,
        "selected_model": selected,
        "compared": compared,
        "test_metrics": compared[selected],
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "leakage_warning": leakage_warning,
        "class_balance": {
            "positive": float(y.mean()),
            "negative": float(1 - y.mean()),
        },
    }


def train_recovery_model(tables: dict[str, pd.DataFrame], random_state: int) -> dict[str, Any]:
    X, y, event_ids = build_recovery_training_set(tables)
    if y.nunique() < 2:
        raise ValueError("Recovery training set must contain both classes")
    result = _fit_and_compare(
        X,
        y,
        RECOVERY_NUMERIC_FEATURES,
        RECOVERY_CATEGORICAL_FEATURES,
        random_state,
    )
    result["task"] = "recovery"
    result["feature_schema"] = {
        "numeric": list(RECOVERY_NUMERIC_FEATURES),
        "categorical": list(RECOVERY_CATEGORICAL_FEATURES),
        "ordered_input_columns": list(RECOVERY_FEATURE_COLUMNS),
    }
    result["n_rows"] = int(len(X))
    result["ids_sample"] = event_ids.head(5).tolist()
    return result


def train_churn_model(tables: dict[str, pd.DataFrame], random_state: int) -> dict[str, Any]:
    X, y, customer_ids = build_churn_training_set(tables)
    if y.nunique() < 2:
        raise ValueError("Churn training set must contain both classes")
    result = _fit_and_compare(
        X,
        y,
        CHURN_NUMERIC_FEATURES,
        CHURN_CATEGORICAL_FEATURES,
        random_state,
    )
    result["task"] = "churn"
    result["feature_schema"] = {
        "numeric": list(CHURN_NUMERIC_FEATURES),
        "categorical": list(CHURN_CATEGORICAL_FEATURES),
        "ordered_input_columns": list(CHURN_FEATURE_COLUMNS),
    }
    result["n_rows"] = int(len(X))
    result["ids_sample"] = customer_ids.head(5).tolist()
    return result


def persist_training_results(
    recovery: dict[str, Any],
    churn: dict[str, Any],
    artifacts_dir: Path,
    random_state: int,
    data_dir: Path,
) -> None:
    models_dir = artifacts_dir / "models"
    metrics_dir = artifacts_dir / "metrics"
    models_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(recovery["pipeline"], models_dir / "recovery_model.joblib")
    joblib.dump(churn["pipeline"], models_dir / "churn_model.joblib")

    (models_dir / "recovery_feature_schema.json").write_text(
        json.dumps(recovery["feature_schema"], indent=2),
        encoding="utf-8",
    )
    (models_dir / "churn_feature_schema.json").write_text(
        json.dumps(churn["feature_schema"], indent=2),
        encoding="utf-8",
    )

    recovery_metrics = {
        "task": "recovery",
        "selected_model": recovery["selected_model"],
        "compared_models": recovery["compared"],
        "selected_test_metrics": recovery["test_metrics"],
        "class_balance": recovery["class_balance"],
        "n_rows": recovery["n_rows"],
        "leakage_warning": recovery["leakage_warning"],
        "model_version": MODEL_VERSION,
    }
    churn_metrics = {
        "task": "churn",
        "selected_model": churn["selected_model"],
        "compared_models": churn["compared"],
        "selected_test_metrics": churn["test_metrics"],
        "class_balance": churn["class_balance"],
        "n_rows": churn["n_rows"],
        "leakage_warning": churn["leakage_warning"],
        "model_version": MODEL_VERSION,
    }
    (metrics_dir / "recovery_metrics.json").write_text(json.dumps(recovery_metrics, indent=2), encoding="utf-8")
    (metrics_dir / "churn_metrics.json").write_text(json.dumps(churn_metrics, indent=2), encoding="utf-8")

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "random_seed": random_state,
        "data_dir": str(data_dir),
        "recovery": {
            "selected_model": recovery["selected_model"],
            "features": recovery["feature_schema"],
            "n_rows": recovery["n_rows"],
            "n_train": recovery["n_train"],
            "n_test": recovery["n_test"],
            "test_roc_auc": recovery["test_metrics"]["roc_auc"],
        },
        "churn": {
            "selected_model": churn["selected_model"],
            "features": churn["feature_schema"],
            "n_rows": churn["n_rows"],
            "n_train": churn["n_train"],
            "n_test": churn["n_test"],
            "test_roc_auc": churn["test_metrics"]["roc_auc"],
        },
    }
    (metrics_dir / "training_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def train_and_persist(
    data_dir: Path | None = None,
    artifacts_dir: Path | None = None,
    random_state: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    data_path = data_dir or (settings.data_path / "demo")
    art_path = artifacts_dir or settings.artifacts_path
    seed = settings.random_seed if random_state is None else random_state
    loaded = load_directory(data_path)
    tables = loaded["tables"]
    recovery = train_recovery_model(tables, seed)
    churn = train_churn_model(tables, seed)
    persist_training_results(recovery, churn, art_path, seed, data_path)
    return {
        "recovery_selected": recovery["selected_model"],
        "churn_selected": churn["selected_model"],
        "recovery_auc": recovery["test_metrics"]["roc_auc"],
        "churn_auc": churn["test_metrics"]["roc_auc"],
        "recovery_leakage_warning": recovery["leakage_warning"],
        "churn_leakage_warning": churn["leakage_warning"],
        "artifacts_dir": str(art_path),
    }
