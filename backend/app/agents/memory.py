"""Lightweight workflow memory: persist iteration steps into EventContext history."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.entities import EventContext, Intervention
from app.agents.state import AgentState


def merge_executed_intervention(state: AgentState) -> dict:
    context = EventContext.model_validate(state["event_context"])
    tool = state.get("tool_result") or {}
    outcome = state.get("outcome") or {}
    selected = state.get("selected_action") or {}
    if not tool:
        return context.model_dump(mode="json")
    ts = tool.get("timestamp")
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00")) if ts else datetime.now(timezone.utc)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    intervention = Intervention(
        intervention_id=str(tool.get("execution_id") or f"WF_{state.get('iteration')}"),
        event_id=context.event.event_id,
        customer_id=context.event.customer_id,
        action_type=str(selected.get("action_type") or tool.get("action_type") or "unknown"),
        action_timestamp=parsed,
        attempt_number=int(state.get("iteration") or 1),
        outcome=str(outcome.get("outcome") or "unknown"),
        amount_recovered=float(outcome.get("amount_recovered") or 0),
    )
    history = list(context.previous_interventions) + [intervention]
    return context.model_copy(update={"previous_interventions": history}).model_dump(mode="json")


def snapshot_iteration(state: AgentState) -> dict:
    return {
        "iteration": int(state.get("iteration") or 1),
        "action_type": (state.get("selected_action") or {}).get("action_type"),
        "guardrail": (state.get("guardrail_result") or {}).get("status"),
        "outcome": (state.get("outcome") or {}).get("outcome"),
        "amount_recovered": (state.get("outcome") or {}).get("amount_recovered"),
        "execution_id": (state.get("tool_result") or {}).get("execution_id"),
    }
