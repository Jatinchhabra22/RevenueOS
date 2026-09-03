"""Deterministic simulated recovery outcomes. No ground-truth labels."""

from __future__ import annotations

import hashlib
import math

from app.schemas.entities import EventContext


def _unit_interval(seed: str) -> float:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def adjusted_success_probability(action_type: str, failure_reason: str | None, base: float) -> float:
    reason = failure_reason or ""
    delta = 0.0
    if action_type == "retry_now" and reason in {"network_error", "payment_timeout"}:
        delta = 0.18
    elif action_type == "retry_now" and reason == "card_expired":
        delta = -0.28
    elif action_type == "retry_later" and reason == "insufficient_funds":
        delta = 0.12
    elif action_type == "payment_method_update" and reason == "card_expired":
        delta = 0.22
    elif action_type == "generate_payment_link":
        delta = 0.08
    elif action_type == "send_email":
        delta = -0.05
    elif action_type == "retention_offer":
        delta = 0.05
    elif action_type == "stop_recovery":
        return 0.0
    return float(min(max(base + delta, 0.02), 0.95))


def simulate_outcome(
    *,
    action_type: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> tuple[str, float]:
    if action_type == "stop_recovery":
        return "NO_ACTION", 0.0
    base = recovery_probability if math.isfinite(recovery_probability) else 0.0
    p = adjusted_success_probability(action_type, context.event.failure_reason, base)
    draw = _unit_interval(f"{workflow_id}:{context.event.event_id}:{action_type}")
    if draw < p:
        recovered = max(float(context.event.amount_at_risk), 0.0)
        if not math.isfinite(recovered):
            recovered = 0.0
        return "RECOVERED", recovered
    if action_type in {"send_email", "generate_payment_link", "payment_method_update"} and draw < p + 0.12:
        return "PENDING", 0.0
    return "NOT_RECOVERED", 0.0
