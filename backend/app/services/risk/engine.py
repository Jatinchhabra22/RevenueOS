"""Deterministic revenue risk scoring and opportunity ranking."""

from __future__ import annotations

import math

from app.core.risk_config import RiskEngineConfig, get_risk_config
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction
from app.schemas.risk import ComponentScores, RiskAssessment

URGENCY_ALIASES = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "med": "medium",
    "low": "low",
}


class RiskEngineError(ValueError):
    """Invalid inputs that must not be scored silently."""


def _require_finite(name: str, value: float) -> float:
    if not math.isfinite(value):
        raise RiskEngineError(f"{name} must be a finite number, got {value}")
    return value


def _require_amount(amount: float) -> float:
    value = _require_finite("amount_at_risk", float(amount))
    if value < 0:
        raise RiskEngineError(f"amount_at_risk must be >= 0, got {value}")
    return value


def _require_probability(name: str, value: float) -> float:
    number = _require_finite(name, float(value))
    if number < 0.0 or number > 1.0:
        # Tolerate tiny float noise around the bounds, reject true invalids.
        if -1e-9 <= number < 0.0:
            return 0.0
        if 1.0 < number <= 1.0 + 1e-9:
            return 1.0
        raise RiskEngineError(f"{name} must be between 0 and 1 inclusive, got {number}")
    return number


def expected_recovery_value(amount_at_risk: float, recovery_probability: float) -> float:
    amount = _require_amount(amount_at_risk)
    probability = _require_probability("recovery_probability", recovery_probability)
    return round(amount * probability, 6)


def _normalize_rupees(value: float, reference: float) -> float:
    if value <= 0:
        return 0.0
    return min(value / reference, 1.0)


def _urgency_score(raw: str | None, config: RiskEngineConfig) -> tuple[float, str, bool]:
    if raw is None or str(raw).strip() == "":
        return config.urgency_missing, "unknown", True
    key = str(raw).strip().lower()
    mapped = URGENCY_ALIASES.get(key)
    if mapped == "high":
        return config.urgency_high, "high", False
    if mapped == "medium":
        return config.urgency_medium, "medium", False
    if mapped == "low":
        return config.urgency_low, "low", False
    return config.urgency_missing, "unknown", True


def _priority_category(score: float, config: RiskEngineConfig) -> str:
    if score >= config.threshold_critical:
        return "CRITICAL"
    if score >= config.threshold_high:
        return "HIGH"
    if score >= config.threshold_medium:
        return "MEDIUM"
    return "LOW"


def _inr(value: float) -> str:
    return f"₹{value:,.0f}"


def _contributing_factors(
    *,
    category: str,
    erv: float,
    n_erv: float,
    ltv: float | None,
    n_ltv: float,
    churn: float,
    urgency_label: str,
    n_urgency: float,
    recovery_probability: float,
    amount_at_risk: float,
    missing_ltv: bool,
    missing_urgency: bool,
) -> list[str]:
    factors: list[str] = []
    if n_erv >= 0.55:
        erv_line = (
            f"High expected recoverable revenue ({_inr(erv)} from {_inr(amount_at_risk)} "
            f"at {recovery_probability:.0%} recovery probability)"
        )
    elif n_erv <= 0.08:
        erv_line = f"Limited expected recoverable revenue ({_inr(erv)})"
    else:
        erv_line = (
            f"Expected recoverable revenue is {_inr(erv)} "
            f"({recovery_probability:.0%} × {_inr(amount_at_risk)})"
        )
    factors.append(f"{category} priority because: {erv_line}")

    if missing_ltv:
        factors.append("Customer lifetime value is unavailable; the customer-value signal is treated as zero")
    elif n_ltv >= 0.5:
        factors.append(f"High customer lifetime value ({_inr(ltv or 0)})")
    elif n_ltv >= 0.2:
        factors.append(f"Material customer lifetime value ({_inr(ltv or 0)})")

    if churn >= 0.6:
        factors.append(f"Elevated churn probability ({churn:.0%})")
    elif churn >= 0.35:
        factors.append(f"Moderate churn probability ({churn:.0%})")
    elif n_erv < 0.15 and churn <= 0.15:
        factors.append(f"Low churn probability ({churn:.0%})")

    if missing_urgency:
        factors.append("Urgency was missing; a medium-default urgency signal was applied")
    elif urgency_label == "high":
        factors.append("Event urgency is high")
    elif urgency_label == "low" and n_erv < 0.2:
        factors.append("Event urgency is low")

    return factors


def assess_revenue_risk(
    context: EventContext,
    recovery: RecoveryPrediction,
    churn: ChurnPrediction,
    config: RiskEngineConfig | None = None,
) -> RiskAssessment:
    settings = config or get_risk_config()
    amount = _require_amount(context.event.amount_at_risk)
    p_recovery = _require_probability("recovery_probability", recovery.probability)
    p_churn = _require_probability("churn_probability", churn.probability)
    erv = expected_recovery_value(amount, p_recovery)

    ltv_raw = context.customer.customer_ltv if context.customer else None
    missing_ltv = ltv_raw is None
    ltv = 0.0 if missing_ltv else _require_finite("customer_ltv", float(ltv_raw))
    if ltv < 0:
        raise RiskEngineError(f"customer_ltv must be >= 0, got {ltv}")

    n_erv = _normalize_rupees(erv, settings.erv_reference)
    n_ltv = _normalize_rupees(ltv, settings.ltv_reference)
    n_urgency, urgency_label, missing_urgency = _urgency_score(context.event.urgency, settings)

    combined = (
        settings.weight_expected_recovery * n_erv
        + settings.weight_customer_value * n_ltv
        + settings.weight_churn_risk * p_churn
        + settings.weight_urgency * n_urgency
    )
    priority_score = round(min(max(combined * 100.0, 0.0), 100.0), 4)
    category = _priority_category(priority_score, settings)
    factors = _contributing_factors(
        category=category,
        erv=erv,
        n_erv=n_erv,
        ltv=None if missing_ltv else ltv,
        n_ltv=n_ltv,
        churn=p_churn,
        urgency_label=urgency_label,
        n_urgency=n_urgency,
        recovery_probability=p_recovery,
        amount_at_risk=amount,
        missing_ltv=missing_ltv,
        missing_urgency=missing_urgency,
    )
    return RiskAssessment(
        event_id=context.event.event_id,
        customer_id=context.event.customer_id,
        amount_at_risk=amount,
        recovery_probability=p_recovery,
        churn_probability=p_churn,
        customer_ltv=None if missing_ltv else ltv,
        urgency=urgency_label,
        expected_recovery_value=erv,
        priority_score=priority_score,
        priority_category=category,  # type: ignore[arg-type]
        component_scores=ComponentScores(
            expected_recovery=round(n_erv, 6),
            customer_value=round(n_ltv, 6),
            churn_risk=round(p_churn, 6),
            urgency=round(n_urgency, 6),
        ),
        contributing_factors=factors,
    )


def rank_opportunities(assessments: list[RiskAssessment]) -> list[RiskAssessment]:
    return sorted(
        assessments,
        key=lambda item: (
            -item.priority_score,
            -item.expected_recovery_value,
            item.event_id,
        ),
    )
