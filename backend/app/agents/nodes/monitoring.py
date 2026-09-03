from __future__ import annotations

from datetime import datetime, timezone

from app.agents.audit import append_audit, require_context
from app.agents.state import AgentState
from app.schemas.agent import RecoveryOutcome, ToolResult


def monitor_result_node(state: AgentState) -> AgentState:
    context = require_context(state)
    tool = state.get("tool_result")
    if not tool:
        outcome = RecoveryOutcome(
            outcome="BLOCKED",
            action_type="none",
            execution_status="skipped",
            remaining_amount_at_risk=context.event.amount_at_risk,
            customer_impact="No intervention executed.",
            timestamp=datetime.now(timezone.utc),
            explanation="No tool result was available to monitor.",
        )
    else:
        result = ToolResult.model_validate(tool)
        simulated = result.metadata.get("simulated_outcome", "NOT_RECOVERED")
        recovered = float(result.metadata.get("simulated_amount_recovered") or 0)
        remaining = max(context.event.amount_at_risk - recovered, 0.0)
        impact = {
            "RECOVERED": "Payment recovered; immediate revenue risk closed.",
            "NOT_RECOVERED": "Intervention did not recover the payment.",
            "PENDING": "Customer action still pending; revenue remains at risk.",
            "NO_ACTION": "Recovery workflow stopped by policy.",
            "BLOCKED": "Intervention was not executed.",
        }.get(str(simulated), "Outcome recorded.")
        outcome = RecoveryOutcome(
            outcome=simulated,  # type: ignore[arg-type]
            action_type=result.action_type,
            execution_status=result.status,
            amount_recovered=recovered,
            remaining_amount_at_risk=remaining,
            customer_impact=impact,
            timestamp=result.timestamp,
            explanation=result.message,
        )
    trail = append_audit(
        state,
        "monitor_result",
        outcome.outcome,
        outcome.explanation,
        {"amount_recovered": outcome.amount_recovered},
    )
    return {"outcome": outcome.model_dump(mode="json"), "audit_trail": trail, "next_step": "reflect_outcome"}
