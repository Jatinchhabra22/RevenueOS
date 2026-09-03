"""Deterministic eligible-action generation. LLM may only choose among these."""

from __future__ import annotations

from app.core.agent_policy import AgentPolicy, get_agent_policy
from app.schemas.agent import CandidateAction
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction
from app.schemas.risk import RiskAssessment

ACTION_ALIASES = {
    "payment_link": "generate_payment_link",
    "email": "send_email",
    "retry_payment": "retry_now",
    "no_action": "stop_recovery",
}

COMPATIBLE: dict[str, tuple[str, ...]] = {
    "network_error": ("retry_now", "retry_later", "stop_recovery"),
    "payment_timeout": ("retry_now", "retry_later", "generate_payment_link", "stop_recovery"),
    "technical_error": ("retry_later", "generate_payment_link", "stop_recovery"),
    "insufficient_funds": ("retry_later", "generate_payment_link", "send_email", "stop_recovery"),
    "card_expired": ("payment_method_update", "generate_payment_link", "send_email", "stop_recovery"),
    "bank_declined": ("generate_payment_link", "payment_method_update", "stop_recovery"),
    "authentication_failed": ("generate_payment_link", "send_email", "stop_recovery"),
    "upi_failure": ("generate_payment_link", "retry_later", "stop_recovery"),
}

META = {
    "retry_now": ("Immediate retry of the same instrument.", "low"),
    "retry_later": ("Delayed retry / short grace window.", "low"),
    "generate_payment_link": ("Alternate payment path via a payment link.", "medium"),
    "send_email": ("Low-friction payment reminder.", "low"),
    "payment_method_update": ("Ask the customer to replace the payment instrument.", "medium"),
    "retention_offer": ("Retention-aware intervention for high-value churn risk.", "high"),
    "stop_recovery": ("Stop automated recovery for this event.", "low"),
}

EFFECT = {
    ("retry_now", "network_error"): "high",
    ("retry_now", "card_expired"): "low",
    ("retry_later", "insufficient_funds"): "medium",
    ("payment_method_update", "card_expired"): "high",
    ("generate_payment_link", "card_expired"): "medium",
    ("retention_offer", ""): "medium",
    ("stop_recovery", ""): "none",
}


def _canonical(name: str) -> str:
    return ACTION_ALIASES.get(name, name)


def generate_candidate_actions(
    context: EventContext,
    churn: ChurnPrediction | None = None,
    risk: RiskAssessment | None = None,
    policy: AgentPolicy | None = None,
) -> list[CandidateAction]:
    settings = policy or get_agent_policy()
    allowed = {_canonical(name) for name in settings.allowed_actions}
    reason = context.event.failure_reason or "unknown"
    types = list(COMPATIBLE.get(reason, ("generate_payment_link", "send_email", "stop_recovery")))

    churn_p = churn.probability if churn else 0.0
    ltv = context.customer.customer_ltv if context.customer else 0.0
    if churn_p >= 0.6 and (ltv or 0) >= 40_000 and "retention_offer" in allowed:
        if "retention_offer" not in types:
            types.insert(-1, "retention_offer")
        types = [item for item in types if item != "retry_now"]

    if risk and risk.expected_recovery_value < 100 and "stop_recovery" not in types:
        types.append("stop_recovery")

    previous = {item.action_type for item in context.previous_interventions}
    # Always allow an explicit stop if the event is still open.
    if "stop_recovery" in allowed and "stop_recovery" not in types:
        types.append("stop_recovery")

    candidates: list[CandidateAction] = []
    for index, action_type in enumerate(types, start=1):
        if action_type not in allowed:
            continue
        rationale, friction = META[action_type]
        expected = EFFECT.get((action_type, reason), EFFECT.get((action_type, ""), "medium"))
        extra = ""
        if action_type in previous:
            extra = " This action was used before on the event; guardrails may still block it."
        candidates.append(
            CandidateAction(
                action_id=f"{context.event.event_id}-ACT-{index:02d}",
                action_type=action_type,  # type: ignore[arg-type]
                eligibility=True,
                expected_effect=expected,
                friction=friction,  # type: ignore[arg-type]
                estimated_cost="none" if action_type == "stop_recovery" else friction,  # type: ignore[arg-type]
                rationale=rationale + extra,
                required_inputs=["event_id"],
            )
        )
    return candidates
