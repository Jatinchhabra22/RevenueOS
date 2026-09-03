from __future__ import annotations

from app.agents.audit import append_audit, optional_churn, require_context
from app.agents.candidates import generate_candidate_actions
from app.agents.state import AgentState
from app.schemas.risk import RiskAssessment


def generate_candidate_actions_node(state: AgentState) -> AgentState:
    context = require_context(state)
    churn = optional_churn(state)
    risk = RiskAssessment.model_validate(state["risk_assessment"]) if state.get("risk_assessment") else None
    candidates = generate_candidate_actions(context, churn=churn, risk=risk)
    trail = append_audit(
        state,
        "generate_candidate_actions",
        ",".join(item.action_type for item in candidates),
        f"Generated {len(candidates)} eligible actions.",
        {"action_ids": [item.action_id for item in candidates]},
    )
    return {
        "candidate_actions": [item.model_dump(mode="json") for item in candidates],
        "audit_trail": trail,
    }
