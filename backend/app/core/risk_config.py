"""Configurable weights and thresholds for the revenue risk engine.

All ranking knobs live here (or in the JSON file this model can load).
Do not scatter magic numbers in scoring code.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app.core.config import get_settings


class RiskEngineConfig(BaseModel):
    weight_expected_recovery: float = 0.45
    weight_customer_value: float = 0.25
    weight_churn_risk: float = 0.20
    weight_urgency: float = 0.10

    # Linear caps used to map rupee values onto [0, 1]
    erv_reference: float = 5_000.0
    ltv_reference: float = 200_000.0

    urgency_high: float = 1.0
    urgency_medium: float = 0.55
    urgency_low: float = 0.20
    urgency_missing: float = 0.40

    # Priority score is 0–100
    threshold_critical: float = 70.0
    threshold_high: float = 50.0
    threshold_medium: float = 30.0

    pursue_min_erv: float = 100.0
    not_recoverable_erv: float = 80.0
    low_recoverability_probability: float = 0.35
    not_recoverable_probability: float = 0.18

    @model_validator(mode="after")
    def weights_must_be_positive_and_sum_to_one(self) -> RiskEngineConfig:
        weights = [
            self.weight_expected_recovery,
            self.weight_customer_value,
            self.weight_churn_risk,
            self.weight_urgency,
        ]
        if any(weight < 0 for weight in weights):
            raise ValueError("Risk engine weights must be non-negative")
        total = sum(weights)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Risk engine weights must sum to 1.0, got {total}")
        if not (self.threshold_critical > self.threshold_high > self.threshold_medium >= 0):
            raise ValueError("Priority thresholds must satisfy CRITICAL > HIGH > MEDIUM >= 0")
        if self.erv_reference <= 0 or self.ltv_reference <= 0:
            raise ValueError("Reference caps must be positive")
        return self


def default_risk_config_path() -> Path:
    settings = get_settings()
    return settings.repo_root / "config" / "risk_engine.json"


def load_risk_config(path: Path | None = None) -> RiskEngineConfig:
    config_path = path or default_risk_config_path()
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("risk_engine.json is not valid JSON") from exc
        return RiskEngineConfig.model_validate(payload)
    return RiskEngineConfig()


@lru_cache
def get_risk_config() -> RiskEngineConfig:
    return load_risk_config()


def clear_risk_config_cache() -> None:
    get_risk_config.cache_clear()
