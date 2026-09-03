"""Recoverability classification from existing predictions, risk, and event context.

Does not recompute ML probabilities or ERV. Does not replace guardrails.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.core.agent_policy import AgentPolicy, get_agent_policy
from app.core.risk_config import RiskEngineConfig, get_risk_config
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction
from app.schemas.risk import RiskAssessment

RecoverabilityClass = Literal[
    "RECOVERABLE",
    "LOW_RECOVERABILITY",
    "NOT_RECOVERABLE",
    "ALREADY_RESOLVED",
    "ACTION_BLOCKED",
    "NEEDS_REVIEW",
]

RESOLVED_STATUSES = {"recovered", "closed", "resolved", "cancelled", "paid", "completed"}
INACTIVE_TRENDS = {"inactive", "dormant", "churned", "lapsed"}

STATEMENTS: dict[str, str] = {
    "RECOVERABLE": "This event is worth pursuing.",
    "LOW_RECOVERABILITY": "This event has low recovery potential.",
    "NOT_RECOVERABLE": "This event should not receive another intervention.",
    "ALREADY_RESOLVED": "This event is already resolved.",
    "ACTION_BLOCKED": "This action is blocked by guardrails.",
    "NEEDS_REVIEW": "This event requires review.",
}


class RecoverabilityAssessment(BaseModel):
    classification: RecoverabilityClass
    pursue: bool
    statement: str
    reason: str
    reason_codes: list[str] = Field(default_factory=list)
    recovery_probability: float | None = None
    expected_recovery_value: float | None = None
    amount_at_risk: float | None = None


def _hours_since(timestamp: datetime | None, *, now: datetime | None = None) -> float | None:
    if timestamp is None:
        return None
    when = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return max((current - when).total_seconds() / 3600.0, 0.0)


def classify_recoverability(
    context: EventContext,
    recovery: RecoveryPrediction | None,
    churn: ChurnPrediction | None,
    risk: RiskAssessment | None,
    *,
    policy: AgentPolicy | None = None,
    config: RiskEngineConfig | None = None,
    now: datetime | None = None,
) -> RecoverabilityAssessment:
    settings = policy or get_agent_policy()
    knobs = config or get_risk_config()
    event = context.event
    customer = context.customer
    status = (event.event_status or "").strip().lower()
    recovery_p = recovery.probability if recovery else (risk.recovery_probability if risk else None)
    erv = risk.expected_recovery_value if risk else None
    if erv is None and recovery_p is not None:
        erv = round(event.amount_at_risk * recovery_p, 6)
    amount = risk.amount_at_risk if risk else event.amount_at_risk
    codes: list[str] = []

    if status in RESOLVED_STATUSES:
        return RecoverabilityAssessment(
            classification="ALREADY_RESOLVED",
            pursue=False,
            statement=STATEMENTS["ALREADY_RESOLVED"],
            reason="Event status is already resolved; no further recovery intervention is justified.",
            reason_codes=["EVENT_ALREADY_RESOLVED"],
            recovery_probability=recovery_p,
            expected_recovery_value=erv,
            amount_at_risk=amount,
        )

    history = list(context.previous_interventions or [])
    if len(history) >= settings.max_interventions_per_event:
        codes.append("MAXIMUM_ATTEMPTS_REACHED")
        return RecoverabilityAssessment(
            classification="ACTION_BLOCKED",
            pursue=False,
            statement=STATEMENTS["ACTION_BLOCKED"],
            reason="Maximum interventions for this event have already been used.",
            reason_codes=codes,
            recovery_probability=recovery_p,
            expected_recovery_value=erv,
            amount_at_risk=amount,
        )

    if history and settings.cooldown_hours > 0:
        last = max((item.action_timestamp for item in history), default=None)
        elapsed = _hours_since(last, now=now)
        if elapsed is not None and elapsed < settings.cooldown_hours:
            codes.append("CONTACT_COOLDOWN_ACTIVE")
            return RecoverabilityAssessment(
                classification="ACTION_BLOCKED",
                pursue=False,
                statement=STATEMENTS["ACTION_BLOCKED"],
                reason="A recent intervention is still inside the configured cooldown window.",
                reason_codes=codes,
                recovery_probability=recovery_p,
                expected_recovery_value=erv,
                amount_at_risk=amount,
            )

    missing_core = not event.failure_reason and customer is None
    if missing_core:
        return RecoverabilityAssessment(
            classification="NEEDS_REVIEW",
            pursue=False,
            statement=STATEMENTS["NEEDS_REVIEW"],
            reason="Failure reason and customer context are both missing, so an automated intervention is not justified.",
            reason_codes=["MISSING_EVENT_CONTEXT"],
            recovery_probability=recovery_p,
            expected_recovery_value=erv,
            amount_at_risk=amount,
        )

    inactive = bool(customer and (customer.activity_trend or "").strip().lower() in INACTIVE_TRENDS)
    attempts = event.attempt_number or 0
    low_p = recovery_p is not None and recovery_p < knobs.low_recoverability_probability
    very_low_p = recovery_p is not None and recovery_p < knobs.not_recoverable_probability
    low_erv = erv is not None and erv < knobs.pursue_min_erv
    tiny_erv = erv is not None and erv < knobs.not_recoverable_erv

    if very_low_p and (tiny_erv or low_erv or inactive or attempts >= 3):
        codes.append("RECOVERY_PROBABILITY_TOO_LOW")
        if tiny_erv or low_erv:
            codes.append("EXPECTED_VALUE_TOO_LOW")
        if inactive:
            codes.append("CUSTOMER_INACTIVE")
        return RecoverabilityAssessment(
            classification="NOT_RECOVERABLE",
            pursue=False,
            statement=STATEMENTS["NOT_RECOVERABLE"],
            reason="Predicted recovery probability and expected recoverable value do not justify another intervention.",
            reason_codes=codes,
            recovery_probability=recovery_p,
            expected_recovery_value=erv,
            amount_at_risk=amount,
        )

    if low_erv and (low_p or (erv is not None and erv < knobs.pursue_min_erv)):
        codes.append("EXPECTED_VALUE_TOO_LOW")
        if low_p:
            codes.append("RECOVERY_PROBABILITY_TOO_LOW")
        classification: RecoverabilityClass = "LOW_RECOVERABILITY"
        pursue = False
        return RecoverabilityAssessment(
            classification=classification,
            pursue=pursue,
            statement=STATEMENTS[classification],
            reason="Expected recoverable value is below the pursue threshold, so no recovery action will be executed.",
            reason_codes=codes,
            recovery_probability=recovery_p,
            expected_recovery_value=erv,
            amount_at_risk=amount,
        )

    if low_p or inactive:
        codes.append("LOW_PREDICTED_RECOVERABILITY" if low_p else "CUSTOMER_INACTIVE")
        return RecoverabilityAssessment(
            classification="LOW_RECOVERABILITY",
            pursue=True,
            statement=STATEMENTS["LOW_RECOVERABILITY"],
            reason="Recovery potential is limited, but expected value is still high enough to consider an eligible action.",
            reason_codes=codes,
            recovery_probability=recovery_p,
            expected_recovery_value=erv,
            amount_at_risk=amount,
        )

    return RecoverabilityAssessment(
        classification="RECOVERABLE",
        pursue=True,
        statement=STATEMENTS["RECOVERABLE"],
        reason="Predicted recoverability and expected recoverable value justify a bounded intervention.",
        reason_codes=["INTERVENTION_JUSTIFIED"],
        recovery_probability=recovery_p,
        expected_recovery_value=erv,
        amount_at_risk=amount,
    )


def prefer_no_action(assessment: RecoverabilityAssessment) -> bool:
    return not assessment.pursue
