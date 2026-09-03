from __future__ import annotations

from datetime import datetime, timezone

from app.agents.audit import append_audit, require_context
from app.agents.state import AgentState
from app.schemas.agent import GuardrailResult, RecoveryOutcome


def route_next_step_node(state: AgentState) -> AgentState:
    if int(state.get("iteration") or 0) > 4:
        trail = append_audit(state, "route_next_step", "finalize", "Max workflow iterations reached.")
        return {"next_step": "finalize", "audit_trail": trail, "error": "max_iterations"}

    guardrail = state.get("guardrail_result")
    if guardrail:
        parsed = GuardrailResult.model_validate(guardrail)
        if not parsed.allowed:
            context = require_context(state)
            selected = state.get("selected_action") or {}
            outcome = RecoveryOutcome(
                outcome="BLOCKED",
                action_type=str(selected.get("action_type") or "none"),
                execution_status="blocked",
                remaining_amount_at_risk=context.event.amount_at_risk,
                customer_impact="Intervention blocked by policy; no tool was invoked.",
                timestamp=datetime.now(timezone.utc),
                explanation=parsed.reason,
            )
            trail = append_audit(state, "route_next_step", "finalize", "Guardrail blocked execution.")
            return {
                "next_step": "finalize",
                "status": "blocked",
                "outcome": outcome.model_dump(mode="json"),
                "audit_trail": trail,
            }

    selected = state.get("selected_action") or {}
    if selected.get("action_type") == "stop_recovery":
        trail = append_audit(state, "route_next_step", "execute_action", "No-action / stop still records an execution.")
        return {"next_step": "execute_action", "audit_trail": trail}

    trail = append_audit(state, "route_next_step", "execute_action", "Proceed to bounded simulated execution.")
    return {"next_step": "execute_action", "audit_trail": trail}


def route_after_guardrails(state: AgentState) -> str:
    return "execute_action" if state.get("next_step") == "execute_action" else "finalize"
