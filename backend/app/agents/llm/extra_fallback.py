"""Deterministic stand-ins when structured LLM output is unavailable or invalid."""

from __future__ import annotations

from app.schemas.agent import CustomerAnalysis, InvestigationResult, ReflectionResult, SupervisorDecision
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction


def fallback_investigation(context: EventContext, *, tools_used: list[str], tool_results: dict) -> InvestigationResult:
    event = context.event
    facts = [
        f"Event {event.event_id} is {event.event_type} with ₹{event.amount_at_risk:,.0f} at risk",
        f"Failure reason: {event.failure_reason or 'unknown'}",
        f"Status: {event.event_status}",
    ]
    if context.customer:
        facts.append(
            f"Customer tenure {context.customer.tenure_days} days; LTV ₹{(context.customer.customer_ltv or 0):,.0f}"
        )
    missing = []
    if context.customer is None:
        missing.append("customer profile")
    if not context.recent_transactions:
        missing.append("recent transactions")
    signals = []
    if event.attempt_number and event.attempt_number >= 2:
        signals.append("repeated attempt on this event")
    if context.previous_interventions:
        signals.append(f"{len(context.previous_interventions)} prior interventions recorded")
    return InvestigationResult(
        facts_found=facts,
        important_signals=signals,
        missing_information=missing,
        anomalies=[],
        evidence_summary=(
            f"Observed {event.failure_reason or 'unknown'} on an open recovery event. "
            "This summary uses tool results only; inferences are labeled in later nodes."
        ),
        confidence=0.7 if context.customer else 0.45,
        source="fallback",
        tools_used=tools_used,
    )


def fallback_customer_analysis(context: EventContext, churn: ChurnPrediction | None) -> CustomerAnalysis:
    customer = context.customer
    ltv = customer.customer_ltv if customer else None
    if ltv is None:
        band = "unknown"
    elif ltv >= 100_000:
        band = "high"
    elif ltv >= 40_000:
        band = "medium"
    else:
        band = "low"
    churn_p = churn.probability if churn else None
    if churn_p is None:
        risk = "unknown"
    elif churn_p >= 0.6:
        risk = "high"
    elif churn_p >= 0.35:
        risk = "medium"
    else:
        risk = "low"
    tone = "low_friction" if risk in {"high", "medium"} and band in {"high", "medium"} else "direct"
    signals = []
    if customer and customer.payment_success_rate is not None:
        signals.append(f"historical payment success {customer.payment_success_rate:.0%}")
    if customer and customer.activity_trend:
        signals.append(f"activity trend {customer.activity_trend}")
    return CustomerAnalysis(
        customer_value_band=band,
        churn_risk=risk,
        relationship_strength="strong" if (ltv or 0) >= 40_000 else "limited",
        contact_sensitivity="high" if risk == "high" else "medium",
        recovery_sensitivity="high" if risk == "high" else "medium",
        recommended_tone=tone,
        key_customer_signals=signals,
        summary=(
            f"Value band {band}; churn signal {risk}"
            + (f" (model P(churn)={churn_p:.0%})" if churn_p is not None else "")
            + ". ML probability is a fact, not rewritten."
        ),
        source="fallback",
        ml_churn_probability=churn_p,
    )


def fallback_reflection(
    *,
    outcome: str,
    action_type: str,
    iteration: int,
    max_iterations: int,
    has_alternative: bool,
) -> ReflectionResult:
    if outcome == "RECOVERED":
        return ReflectionResult(
            outcome_interpretation="The simulated intervention recovered the amount at risk.",
            strategy_assessment="The selected action achieved the recovery goal.",
            new_information="Revenue is no longer at risk for this event.",
            recommended_next_step="RECOVERED",
            avoid_actions=[],
            confidence=0.8,
            summary="Stop. Money recovered.",
            source="fallback",
        )
    if outcome in {"PENDING", "WAITING_FOR_CUSTOMER"}:
        return ReflectionResult(
            outcome_interpretation="Customer action is still required.",
            strategy_assessment="Further automated charges may add friction.",
            new_information="Waiting on the customer.",
            recommended_next_step="WAIT_FOR_CUSTOMER",
            avoid_actions=[action_type],
            confidence=0.6,
            summary="Pause automated recovery until the customer responds.",
            source="fallback",
        )
    if outcome in {"BLOCKED", "NO_ACTION", "ESCALATED"}:
        return ReflectionResult(
            outcome_interpretation="No further automated execution is appropriate.",
            strategy_assessment="Policy or stop decision ended the loop.",
            new_information="",
            recommended_next_step="STOP_RECOVERY",
            avoid_actions=[action_type],
            confidence=0.7,
            summary="Terminal. Do not execute another tool.",
            source="fallback",
        )
    if iteration >= max_iterations or not has_alternative:
        return ReflectionResult(
            outcome_interpretation="The intervention did not recover the payment.",
            strategy_assessment="No productive automated alternative remains within limits.",
            new_information="",
            recommended_next_step="STOP_RECOVERY",
            avoid_actions=[action_type],
            confidence=0.6,
            summary="Stop. Limits or candidates exhausted.",
            source="fallback",
        )
    return ReflectionResult(
        outcome_interpretation="The intervention did not recover the payment.",
        strategy_assessment="A different eligible action may still be attempted.",
        new_information=f"Last action {action_type} did not recover.",
        recommended_next_step="CONTINUE",
        avoid_actions=[action_type],
        confidence=0.55,
        summary="Continue with another bounded eligible action.",
        source="fallback",
    )


def fallback_supervisor(*, missing: str | None, reflection: ReflectionResult | None, recovered: bool) -> SupervisorDecision:
    if recovered:
        return SupervisorDecision(route="RECOVERED", reason="Observed recovery is terminal.", source="fallback")
    if missing == "investigation":
        return SupervisorDecision(route="INVESTIGATE", reason="Evidence has not been gathered.", source="fallback")
    if missing == "diagnosis":
        return SupervisorDecision(route="DIAGNOSE", reason="Root cause has not been recorded.", source="fallback")
    if missing == "customer":
        return SupervisorDecision(route="ANALYZE_CUSTOMER", reason="Customer analysis is missing.", source="fallback")
    if reflection is None:
        return SupervisorDecision(route="STRATEGIZE", reason="Ready to evaluate eligible actions.", source="fallback")
    mapping = {
        "CONTINUE": "STRATEGIZE",
        "WAIT_FOR_CUSTOMER": "WAIT_FOR_CUSTOMER",
        "ESCALATE_TO_MERCHANT": "ESCALATE_TO_MERCHANT",
        "STOP_RECOVERY": "STOP_RECOVERY",
        "RECOVERED": "RECOVERED",
    }
    route = mapping.get(reflection.recommended_next_step, "STOP_RECOVERY")
    return SupervisorDecision(
        route=route,  # type: ignore[arg-type]
        reason=reflection.summary or reflection.outcome_interpretation,
        source="fallback",
    )
