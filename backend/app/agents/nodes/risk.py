from __future__ import annotations

from app.agents.audit import append_audit, optional_churn, optional_recovery, require_context
from app.agents.state import AgentState
from app.services.risk.engine import assess_revenue_risk


def assess_revenue_risk_node(state: AgentState) -> AgentState:
    if state.get("risk_assessment"):
        trail = append_audit(state, "assess_revenue_risk", "injected", "Risk assessment already present.")
        return {"audit_trail": trail}

    context = require_context(state)
    recovery = optional_recovery(state)
    churn = optional_churn(state)
    if recovery is None or churn is None:
        raise ValueError("Risk assessment requires recovery and churn predictions")
    assessment = assess_revenue_risk(context, recovery, churn)
    trail = append_audit(
        state,
        "assess_revenue_risk",
        assessment.priority_category,
        f"ERV ₹{assessment.expected_recovery_value:,.0f}; score {assessment.priority_score:.1f}.",
    )
    return {
        "risk_assessment": assessment.model_dump(mode="json"),
        "audit_trail": trail,
    }
