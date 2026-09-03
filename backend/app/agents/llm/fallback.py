"""Deterministic diagnosis and action selection when no LLM is available."""

from __future__ import annotations

from app.schemas.agent import ActionDecision, CandidateAction, Diagnosis
from app.schemas.outcomes import LearningSignal
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction
from app.schemas.risk import RiskAssessment

ISSUE_BY_REASON = {
    "card_expired": "expired_payment_method",
    "insufficient_funds": "temporary_liquidity",
    "network_error": "temporary_technical_failure",
    "payment_timeout": "temporary_technical_failure",
    "technical_error": "temporary_technical_failure",
    "authentication_failed": "authentication_friction",
    "bank_declined": "issuer_decline",
    "upi_failure": "upi_failure",
}


def fallback_diagnosis(
    context: EventContext,
    recovery: RecoveryPrediction | None = None,
    churn: ChurnPrediction | None = None,
) -> Diagnosis:
    event = context.event
    customer = context.customer
    reason = (event.failure_reason or "unknown").replace("_", " ")
    issue = ISSUE_BY_REASON.get(event.failure_reason or "", "payment_failure")
    tenure = f"{customer.tenure_days} days tenure" if customer and customer.tenure_days is not None else "unknown tenure"
    success = (
        f"{customer.payment_success_rate:.0%} historical success"
        if customer and customer.payment_success_rate is not None
        else "unknown payment reliability"
    )
    ltv = customer.customer_ltv if customer else None
    churn_p = churn.probability if churn else None
    recovery_p = recovery.probability if recovery else None

    if event.failure_reason == "card_expired":
        strategy = "Ask the customer to update the payment method rather than retrying the same instrument."
        recoverability = "Retrying the expired instrument is unlikely to recover the payment."
    elif event.failure_reason in {"network_error", "payment_timeout", "technical_error"}:
        strategy = "A low-friction retry is appropriate for a likely transient failure."
        recoverability = "Temporary technical failures are often recoverable with a retry."
    elif event.failure_reason == "insufficient_funds":
        strategy = "Delay the retry or send a payment link instead of an immediate second charge."
        recoverability = "Funds issues can recover with time or an alternate payment path."
    else:
        strategy = "Use a bounded, low-friction intervention from the eligible set."
        recoverability = "Recoverability depends on failure type, history, and customer value."

    churn_concern = "Churn risk is unknown from current context."
    if churn_p is not None and ltv and ltv >= 50_000 and churn_p >= 0.45:
        churn_concern = (
            f"Churn probability is {churn_p:.0%} with material LTV ₹{ltv:,.0f}; avoid aggressive retries."
        )
    elif churn_p is not None:
        churn_concern = f"Churn probability is {churn_p:.0%}."

    factors = [f"Failure reason: {reason}", f"Amount at risk: ₹{event.amount_at_risk:,.0f}", tenure, success]
    if recovery_p is not None:
        factors.append(f"Model recovery probability: {recovery_p:.0%}")

    return Diagnosis(
        primary_issue=f"{reason} on a {event.event_type.replace('_', ' ')} event",
        recoverability_reason=recoverability,
        churn_concern=churn_concern,
        customer_context=f"{tenure}; {success}",
        recommended_strategy=strategy,
        issue_category=issue,
        event_summary=(
            f"{event.event_type} of ₹{event.amount_at_risk:,.0f} failed due to {reason} "
            f"(attempt {event.attempt_number or 1})."
        ),
        key_factors=factors,
        risk_notes=["Diagnosis is explanatory only and does not invent probabilities."],
        source="fallback",
    )


def _signal_maps(historical: list[LearningSignal] | list[dict] | None) -> list[LearningSignal]:
    parsed: list[LearningSignal] = []
    for item in historical or []:
        if isinstance(item, LearningSignal):
            parsed.append(item)
        else:
            try:
                parsed.append(LearningSignal.model_validate(item))
            except Exception:
                continue
    return parsed


def apply_historical_intelligence(
    chosen: CandidateAction,
    candidates: list[CandidateAction],
    *,
    segment: str | None,
    historical: list[LearningSignal] | list[dict] | None,
) -> tuple[CandidateAction, int | None, str | None]:
    """Prefer a historically stronger *eligible* action. Never invent actions."""
    signals = [
        item
        for item in _signal_maps(historical)
        if item.segment == segment and item.observations >= 5 and item.observed_recovery_rate is not None
    ]
    eligible = {item.action_type: item for item in candidates}
    scored = [item for item in signals if item.action_type in eligible]
    matching_chosen = next((item for item in _signal_maps(historical) if item.action_type == chosen.action_type and item.segment == segment), None)
    if not scored:
        if matching_chosen and matching_chosen.observations >= 5:
            note = (
                f"Decision informed by {matching_chosen.observations} historical observations "
                f"for this action/segment (sample quality: {matching_chosen.sample_quality})."
            )
            return chosen, matching_chosen.observations, note
        return chosen, None, None
    scored.sort(key=lambda item: (item.observed_recovery_rate or 0.0, item.observations), reverse=True)
    best = scored[0]
    best_action = eligible[best.action_type]
    if best.action_type != chosen.action_type:
        note = (
            f"Historical observations for segment '{segment}' favored {best.action_type} "
            f"({best.observed_recovery_rate:.0%} over {best.observations} executions) "
            f"among already-eligible actions. Guardrails still apply after selection."
        )
        return best_action, best.observations, note
    note = (
        f"Decision informed by {best.observations} historical observations for this action/segment."
    )
    return chosen, best.observations, note


def annotate_decision_with_history(
    decision: ActionDecision,
    *,
    action_type: str,
    segment: str | None,
    historical: list[LearningSignal] | list[dict] | None,
) -> ActionDecision:
    matching = next(
        (
            item
            for item in _signal_maps(historical)
            if item.action_type == action_type and item.segment == segment and item.observations >= 5
        ),
        None,
    )
    if matching is None:
        return decision
    note = (
        f"Decision informed by {matching.observations} historical observations for this action/segment."
    )
    return decision.model_copy(
        update={
            "informed_by_observations": matching.observations,
            "historical_note": note,
        }
    )


def fallback_select_action(
    candidates: list[CandidateAction],
    context: EventContext,
    recovery: RecoveryPrediction | None,
    churn: ChurnPrediction | None,
    risk: RiskAssessment | None,
    historical: list[LearningSignal] | list[dict] | None = None,
    avoid_types: list[str] | None = None,
) -> ActionDecision:
    if not candidates:
        raise ValueError("No candidate actions available for fallback selection")

    reason = context.event.failure_reason
    churn_p = churn.probability if churn else 0.0
    ltv = context.customer.customer_ltv if context.customer else 0.0
    blocked = {item for item in (avoid_types or []) if item != "stop_recovery"}
    preferred = {
        "card_expired": "payment_method_update",
        "network_error": "retry_now",
        "payment_timeout": "retry_now",
        "technical_error": "retry_later",
        "insufficient_funds": "retry_later",
        "bank_declined": "generate_payment_link",
        "authentication_failed": "generate_payment_link",
        "upi_failure": "generate_payment_link",
    }.get(reason or "", "")

    if preferred in blocked:
        preferred = ""

    if churn_p >= 0.6 and (ltv or 0) >= 40_000:
        if any(item.action_type == "retention_offer" for item in candidates) and "retention_offer" not in blocked:
            preferred = "retention_offer"
        elif any(item.action_type == "payment_method_update" for item in candidates) and "payment_method_update" not in blocked:
            preferred = "payment_method_update"

    by_type = {item.action_type: item for item in candidates}
    usable = [item for item in candidates if item.action_type not in blocked]
    pool = usable or candidates
    chosen = by_type.get(preferred) if preferred and preferred not in blocked else None
    chosen = chosen if chosen in pool else None
    chosen = chosen or next((item for item in pool if item.action_type != "stop_recovery"), pool[0])
    chosen, informed_by, historical_note = apply_historical_intelligence(
        chosen,
        candidates,
        segment=reason,
        historical=historical,
    )
    alternative = next((item.action_type for item in candidates if item.action_id != chosen.action_id), None)
    why = (
        f"Deterministic policy selected {chosen.action_type} for failure '{reason or 'unknown'}' "
        f"given recovery/churn/priority context."
    )
    if risk:
        why += f" Priority is {risk.priority_category} with ERV ₹{risk.expected_recovery_value:,.0f}."
    if historical_note:
        why += f" {historical_note}"
    return ActionDecision(
        selected_action_id=chosen.action_id,
        selected_action_type=chosen.action_type,
        reason=why,
        confidence=0.55,
        alternative_considered=alternative,
        source="fallback",
        informed_by_observations=informed_by,
        historical_note=historical_note,
    )
