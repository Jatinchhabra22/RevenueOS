"""Append structured agent trace events (audit-friendly, no CoT)."""

from __future__ import annotations

import uuid
from typing import Any

from app.agents.audit import utcnow
from app.agents.state import AgentState
from app.schemas.agent import AgentTraceEvent


def append_trace(
    state: AgentState,
    *,
    agent: str,
    event_type: str,
    summary: str,
    status: str = "ok",
    tool_name: str | None = None,
    decision: str | None = None,
    fallback_used: bool = False,
    duration_ms: float | None = None,
) -> list[dict[str, Any]]:
    trail = list(state.get("agent_trace") or [])
    event = AgentTraceEvent(
        trace_id=f"TR_{uuid.uuid4().hex[:10]}",
        workflow_id=str(state.get("workflow_id") or ""),
        iteration=int(state.get("iteration") or 1),
        agent=agent,
        event_type=event_type,
        timestamp=utcnow(),
        status=status,
        summary=summary,
        tool_name=tool_name,
        decision=decision,
        fallback_used=fallback_used,
        duration_ms=duration_ms,
    )
    trail.append(event.model_dump(mode="json"))
    return trail
