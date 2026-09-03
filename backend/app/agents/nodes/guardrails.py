from __future__ import annotations

from app.agents.audit import append_audit, parse_candidates, require_context
from app.agents.guardrails import validate_guardrails
from app.agents.state import AgentState
from app.schemas.agent import ActionDecision, CandidateAction


def validate_guardrails_node(state: AgentState) -> AgentState:
    context = require_context(state)
    candidates = parse_candidates(state)
    decision = ActionDecision.model_validate(state.get("decision") or {})
    selected = CandidateAction.model_validate(state.get("selected_action") or {})
    result = validate_guardrails(
        selected_action_id=decision.selected_action_id or selected.action_id,
        selected_action_type=decision.selected_action_type or selected.action_type,
        candidates=candidates,
        context=context,
    )
    next_step = "execute_action" if result.allowed else "finalize"
    trail = append_audit(
        state,
        "validate_guardrails",
        result.status,
        result.reason,
        {"violations": result.violations},
    )
    return {
        "guardrail_result": result.model_dump(mode="json"),
        "next_step": next_step,
        "status": "blocked" if not result.allowed else state.get("status") or "started",
        "audit_trail": trail,
    }
