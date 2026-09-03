"""Load persisted models and score EventContext objects."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from app.core.config import get_settings
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction
from app.services.features.churn_features import churn_feature_frame, churn_features_from_context
from app.services.features.constants import CHURN_FEATURE_COLUMNS, RECOVERY_FEATURE_COLUMNS
from app.services.features.recovery_features import recovery_feature_frame, recovery_features_from_context
from app.services.prediction.training import MODEL_VERSION

RECOVERY_HEURISTICS = {
    "network_error": 0.72,
    "payment_timeout": 0.68,
    "technical_error": 0.64,
    "insufficient_funds": 0.48,
    "authentication_failed": 0.42,
    "upi_failure": 0.40,
    "bank_declined": 0.28,
    "card_expired": 0.22,
}


def _band(probability: float, high: float, mid: float) -> str:
    if probability >= high:
        return "high"
    if probability >= mid:
        return "medium"
    return "low"


def _clip_proba(value: float) -> float:
    number = float(value)
    if not np.isfinite(number):
        raise ValueError("predicted probability is not a finite number")
    return float(min(max(number, 0.0), 1.0))


@lru_cache
def _load_joblib(path: str) -> Pipeline:
    loaded = joblib.load(path)
    if not isinstance(loaded, Pipeline):
        raise TypeError(f"Expected sklearn Pipeline in {path}")
    return loaded


def _model_path(artifacts_dir: Path | None, filename: str) -> Path:
    root = artifacts_dir or get_settings().artifacts_path
    return root / "models" / filename


def load_recovery_model(artifacts_dir: Path | None = None) -> Pipeline | None:
    path = _model_path(artifacts_dir, "recovery_model.joblib")
    if not path.exists():
        return None
    try:
        return _load_joblib(str(path))
    except Exception:
        return None


def load_churn_model(artifacts_dir: Path | None = None) -> Pipeline | None:
    path = _model_path(artifacts_dir, "churn_model.joblib")
    if not path.exists():
        return None
    try:
        return _load_joblib(str(path))
    except Exception:
        return None


def _transformed_contributions(pipeline: Pipeline, frame: pd.DataFrame) -> list[str]:
    preprocess = pipeline.named_steps["preprocess"]
    model = pipeline.named_steps["model"]
    transformed = preprocess.transform(frame)
    names = list(preprocess.get_feature_names_out())
    if hasattr(model, "coef_"):
        contrib = model.coef_[0] * transformed[0]
        ranking = sorted(zip(names, contrib, strict=False), key=lambda item: abs(item[1]), reverse=True)
        factors = []
        for name, value in ranking[:4]:
            direction = "increases" if value > 0 else "decreases"
            factors.append(f"{name} {direction} the predicted probability (linear contribution)")
        return factors
    if hasattr(model, "feature_importances_"):
        ranking = sorted(zip(names, model.feature_importances_, strict=False), key=lambda item: item[1], reverse=True)
        return [
            f"{name} is globally important in the tree model (not an instance-level explanation)"
            for name, importance in ranking[:4]
            if importance > 0
        ]
    return []


def _predict_frame(pipeline: Pipeline, frame: pd.DataFrame) -> tuple[float, list[str], str]:
    proba = _clip_proba(float(pipeline.predict_proba(frame)[0, 1]))
    model_type = type(pipeline.named_steps["model"]).__name__
    factors = _transformed_contributions(pipeline, frame)
    return proba, factors, model_type


def _recovery_fallback(context: EventContext) -> RecoveryPrediction:
    reason = (context.event.failure_reason or "unknown").strip().lower()
    probability = RECOVERY_HEURISTICS.get(reason, 0.4)
    if context.event.attempt_number and context.event.attempt_number >= 3:
        probability = max(probability - 0.12, 0.08)
    return RecoveryPrediction(
        probability=_clip_proba(probability),
        recoverability=_band(probability, 0.65, 0.4),
        model_type="heuristic_fallback",
        model_version=MODEL_VERSION,
        fallback=True,
        contributing_factors=[
            "Model artifact missing; probability is a failure-reason heuristic, not an ML estimate."
        ],
    )


def _churn_fallback(context: EventContext) -> ChurnPrediction:
    customer = context.customer
    probability = 0.25
    if customer and customer.activity_trend in {"declining", "inactive"}:
        probability += 0.25
    if customer and customer.payment_success_rate is not None:
        probability += 0.3 * (1 - customer.payment_success_rate)
    probability = _clip_proba(probability)
    return ChurnPrediction(
        probability=probability,
        risk_category=_band(probability, 0.6, 0.35),
        model_type="heuristic_fallback",
        model_version=MODEL_VERSION,
        fallback=True,
        contributing_factors=[
            "Model artifact missing; probability is a behavioral heuristic, not an ML estimate."
        ],
    )


def predict_recovery(
    context: EventContext,
    artifacts_dir: Path | None = None,
) -> RecoveryPrediction:
    model = load_recovery_model(artifacts_dir)
    if model is None:
        return _recovery_fallback(context)
    features = recovery_features_from_context(context)
    frame = recovery_feature_frame([features])
    if list(frame.columns) != list(RECOVERY_FEATURE_COLUMNS):
        raise ValueError("Recovery inference columns drifted from training schema")
    try:
        probability, factors, model_type = _predict_frame(model, frame)
    except (ValueError, TypeError):
        fallback = _recovery_fallback(context)
        return fallback.model_copy(
            update={
                "contributing_factors": [
                    "Model artifact produced a non-finite probability; heuristic fallback was used."
                ]
            }
        )
    return RecoveryPrediction(
        probability=probability,
        recoverability=_band(probability, 0.65, 0.4),
        model_type=model_type,
        model_version=MODEL_VERSION,
        fallback=False,
        contributing_factors=factors,
    )


def predict_churn(
    context: EventContext,
    artifacts_dir: Path | None = None,
) -> ChurnPrediction:
    model = load_churn_model(artifacts_dir)
    if model is None:
        return _churn_fallback(context)
    features = churn_features_from_context(context)
    frame = churn_feature_frame([features])
    if list(frame.columns) != list(CHURN_FEATURE_COLUMNS):
        raise ValueError("Churn inference columns drifted from training schema")
    try:
        probability, factors, model_type = _predict_frame(model, frame)
    except (ValueError, TypeError):
        fallback = _churn_fallback(context)
        return fallback.model_copy(
            update={
                "contributing_factors": [
                    "Model artifact produced a non-finite probability; heuristic fallback was used."
                ]
            }
        )
    return ChurnPrediction(
        probability=probability,
        risk_category=_band(probability, 0.6, 0.35),
        model_type=model_type,
        model_version=MODEL_VERSION,
        fallback=False,
        contributing_factors=factors,
    )


def clear_model_cache() -> None:
    _load_joblib.cache_clear()
