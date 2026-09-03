from __future__ import annotations

from app.agents.audit import append_audit
from app.agents.state import AgentState


def finalize_node(state: AgentState) -> AgentState:
    outcome = (state.get("outcome") or {}).get("outcome")
    guardrail = (state.get("guardrail_result") or {}).get("status")
    terminal = state.get("terminal_reason") or state.get("workflow_status")
    if terminal == "WAIT_FOR_CUSTOMER" or outcome in {"PENDING", "WAITING_FOR_CUSTOMER"}:
        status = "waiting"
        decision = "WAIT_FOR_CUSTOMER"
    elif terminal == "ESCALATE_TO_MERCHANT" or outcome == "ESCALATED":
        status = "escalated"
        decision = "ESCALATE_TO_MERCHANT"
    elif outcome == "RECOVERED" or terminal == "RECOVERED":
        status = "completed"
        decision = "RECOVERED"
    elif outcome == "NO_ACTION" or (state.get("selected_action") or {}).get("action_type") == "stop_recovery":
        status = "no_action"
        decision = "STOP"
    elif guardrail == "BLOCK" and not state.get("tool_result"):
        status = "blocked"
        decision = "BLOCKED"
    elif outcome in {"NOT_RECOVERED", "PENDING"}:
        status = "completed"
        decision = str(outcome)
    else:
        status = state.get("status") or "completed"
        decision = str(terminal or "FINALIZED")

    if outcome == "RECOVERED":
        status = "completed"
        decision = "RECOVERED"

    trail = append_audit(state, "finalize", decision, f"Workflow ended with status {status}.")
    from app.agents.trace import append_trace

    trace = append_trace(
        {**state, "agent_trace": state.get("agent_trace") or []},
        agent="supervisor",
        event_type="WORKFLOW_TERMINATED",
        summary=f"Workflow ended with status {status}.",
        decision=decision,
    )
    return {
        "status": status,
        "workflow_status": str(terminal or decision),
        "next_step": "END",
        "audit_trail": trail,
        "agent_trace": trace,
    }
