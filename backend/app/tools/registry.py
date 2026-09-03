"""Bounded simulated payment and messaging tools."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.agent_policy import get_agent_policy
from app.schemas.agent import ToolResult
from app.schemas.entities import EventContext
from app.tools.simulator import simulate_outcome


def _result(action_id: str, action_type: str, message: str, metadata: dict) -> ToolResult:
    return ToolResult(
        action_id=action_id,
        action_type=action_type,
        execution_id=f"EXE_{uuid.uuid4().hex[:12]}",
        status="executed",
        timestamp=datetime.now(timezone.utc),
        message=message,
        metadata=metadata,
    )


def execute_simulated_action(
    *,
    action_id: str,
    action_type: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    if action_type not in set(get_agent_policy().allowed_actions):
        raise ValueError(f"Unknown or disallowed action_type '{action_type}'")
    outcome, amount = simulate_outcome(
        action_type=action_type,
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )
    messages = {
        "retry_now": "Simulated immediate payment retry submitted.",
        "retry_later": "Simulated delayed retry / grace window scheduled.",
        "generate_payment_link": "Simulated payment link generated.",
        "send_email": "Simulated payment reminder emailed.",
        "payment_method_update": "Simulated payment-method update request sent.",
        "retention_offer": "Simulated retention offer issued within policy.",
        "stop_recovery": "Automated recovery stopped for this event.",
    }
    return _result(
        action_id,
        action_type,
        messages.get(action_type, "Simulated action executed."),
        {
            "simulated_outcome": outcome,
            "simulated_amount_recovered": amount,
            "integration": "simulation",
        },
    )
