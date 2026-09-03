"""Read-only investigation tools. Allowlisted names only. No LLM-chosen paths."""

from __future__ import annotations

from typing import Any, Callable

from app.schemas.entities import EventContext
from app.schemas.outcomes import LearningSignal


def get_event_details(context: EventContext, **_: Any) -> dict[str, Any]:
    event = context.event
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "amount_at_risk": event.amount_at_risk,
        "failure_reason": event.failure_reason,
        "payment_method": event.payment_method,
        "attempt_number": event.attempt_number,
        "event_status": event.event_status,
        "urgency": event.urgency,
    }


def get_customer_profile(context: EventContext, **_: Any) -> dict[str, Any]:
    customer = context.customer
    if customer is None:
        return {"missing": True}
    return {
        "customer_id": customer.customer_id,
        "segment": customer.customer_segment,
        "tenure_days": customer.tenure_days,
        "total_spend": customer.total_spend,
        "ltv": customer.customer_ltv,
        "payment_success_rate": customer.payment_success_rate,
        "previous_failures": customer.previous_failures,
        "previous_recoveries": customer.previous_recoveries,
        "engagement_score": customer.engagement_score,
        "activity_trend": customer.activity_trend,
    }


def get_payment_history(context: EventContext, **_: Any) -> dict[str, Any]:
    rows = []
    for item in context.recent_transactions[:8]:
        rows.append(
            {
                "transaction_id": item.transaction_id,
                "status": item.transaction_status,
                "amount": item.amount,
                "failure_reason": item.failure_reason,
                "timestamp": item.transaction_timestamp.isoformat(),
            }
        )
    return {"count": len(context.recent_transactions), "recent": rows}


def get_subscription_context(context: EventContext, **_: Any) -> dict[str, Any]:
    sub = context.subscription
    if sub is None:
        return {"present": False}
    return {
        "present": True,
        "status": sub.subscription_status,
        "recurring_amount": sub.recurring_amount,
        "failed_cycles": sub.failed_cycles,
        "successful_cycles": sub.successful_cycles,
    }


def get_previous_interventions(context: EventContext, **_: Any) -> dict[str, Any]:
    rows = [
        {
            "action_type": item.action_type,
            "outcome": item.outcome,
            "timestamp": item.action_timestamp.isoformat(),
        }
        for item in context.previous_interventions[-8:]
    ]
    return {"count": len(context.previous_interventions), "recent": rows}


def get_recent_payment_failures(context: EventContext, **_: Any) -> dict[str, Any]:
    failed = [
        item.failure_reason or item.transaction_status
        for item in context.recent_transactions
        if (item.transaction_status or "").lower() not in {"success", "captured", "paid"}
    ]
    return {"failure_count": len(failed), "reasons": failed[:8]}


def get_customer_engagement_context(context: EventContext, **_: Any) -> dict[str, Any]:
    customer = context.customer
    if customer is None:
        return {"missing": True}
    return {
        "engagement_score": customer.engagement_score,
        "activity_trend": customer.activity_trend,
        "last_activity_date": customer.last_activity_date.isoformat() if customer.last_activity_date else None,
    }


def get_recovery_prediction(context: EventContext, *, state: dict | None = None, **_: Any) -> dict[str, Any]:
    pred = (state or {}).get("recovery_prediction") or {}
    return {
        "probability": pred.get("probability"),
        "recoverability": pred.get("recoverability"),
        "fallback": pred.get("fallback"),
        "note": "ML signal. Not an action.",
    }


def get_churn_prediction(context: EventContext, *, state: dict | None = None, **_: Any) -> dict[str, Any]:
    pred = (state or {}).get("churn_prediction") or {}
    return {
        "probability": pred.get("probability"),
        "risk_category": pred.get("risk_category"),
        "fallback": pred.get("fallback"),
        "note": "ML signal. Agent must not overwrite it.",
    }


def calculate_revenue_risk(context: EventContext, *, state: dict | None = None, **_: Any) -> dict[str, Any]:
    risk = (state or {}).get("risk_assessment") or {}
    return {
        "amount_at_risk": risk.get("amount_at_risk", context.event.amount_at_risk),
        "expected_recovery_value": risk.get("expected_recovery_value"),
        "priority_category": risk.get("priority_category"),
        "priority_score": risk.get("priority_score"),
    }


def get_action_effectiveness(
    context: EventContext,
    *,
    historical: list | None = None,
    **_: Any,
) -> dict[str, Any]:
    rows = []
    for item in historical or []:
        if isinstance(item, LearningSignal):
            payload = item.model_dump()
        elif isinstance(item, dict):
            payload = item
        else:
            continue
        rows.append(
            {
                "action_type": payload.get("action_type"),
                "segment": payload.get("segment"),
                "observations": payload.get("observations"),
                "observed_recovery_rate": payload.get("observed_recovery_rate"),
                "sample_quality": payload.get("sample_quality"),
            }
        )
    return {"signals": rows[:12], "note": "Observational only. Not causal."}


def get_similar_historical_outcomes(
    context: EventContext,
    *,
    historical: list | None = None,
    **_: Any,
) -> dict[str, Any]:
    segment = context.event.failure_reason
    matched = []
    for item in historical or []:
        payload = item.model_dump() if isinstance(item, LearningSignal) else item
        if isinstance(payload, dict) and payload.get("segment") == segment:
            matched.append(payload)
    return {"segment": segment, "matches": matched[:8]}


INVESTIGATION_TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_event_details": get_event_details,
    "get_customer_profile": get_customer_profile,
    "get_payment_history": get_payment_history,
    "get_subscription_context": get_subscription_context,
    "get_previous_interventions": get_previous_interventions,
    "get_recent_payment_failures": get_recent_payment_failures,
    "get_customer_engagement_context": get_customer_engagement_context,
    "get_recovery_prediction": get_recovery_prediction,
    "get_churn_prediction": get_churn_prediction,
    "calculate_revenue_risk": calculate_revenue_risk,
    "get_action_effectiveness": get_action_effectiveness,
    "get_similar_historical_outcomes": get_similar_historical_outcomes,
}

DEFAULT_INVESTIGATION_PLAN = list(INVESTIGATION_TOOLS.keys())


def run_investigation_tools(
    context: EventContext,
    *,
    state: dict | None = None,
    historical: list | None = None,
    plan: list[str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    used: list[str] = []
    results: dict[str, Any] = {}
    requested = plan or DEFAULT_INVESTIGATION_PLAN
    for name in requested:
        fn = INVESTIGATION_TOOLS.get(name)
        if fn is None:
            continue
        results[name] = fn(context, state=state, historical=historical)
        used.append(name)
    return used, results
