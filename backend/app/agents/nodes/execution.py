from __future__ import annotations

from app.agents.audit import append_audit, optional_recovery, require_context
from app.agents.state import AgentState
from app.schemas.agent import CandidateAction, GuardrailResult
from app.tools.registry import execute_simulated_action


def execute_action_node(state: AgentState) -> AgentState:
    guardrail = GuardrailResult.model_validate(state.get("guardrail_result") or {})
    if not guardrail.allowed:
        trail = append_audit(state, "execute_action", "skipped", "Guardrail blocked execution.")
        return {"audit_trail": trail, "next_step": "finalize"}

    context = require_context(state)
    selected = CandidateAction.model_validate(state.get("selected_action") or {})
    recovery = optional_recovery(state)
    if recovery is None:
        trail = append_audit(
            state,
            "execute_action",
            "skipped",
            "Execution blocked because recovery prediction is missing.",
        )
        return {"audit_trail": trail, "next_step": "finalize", "status": "failed"}
    result = execute_simulated_action(
        action_id=selected.action_id,
        action_type=selected.action_type,
        context=context,
        recovery_probability=recovery.probability,
        workflow_id=str(state.get("workflow_id") or "WF"),
    )
    trail = append_audit(
        state,
        "execute_action",
        result.status,
        result.message,
        {"execution_id": result.execution_id, "action_type": result.action_type},
    )
    return {
        "tool_result": result.model_dump(mode="json"),
        "next_step": "monitor_result",
        "audit_trail": trail,
    }
