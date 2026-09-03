from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit, require_context
from app.agents.llm.extra_fallback import fallback_investigation
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.prompts import INVESTIGATOR_SYSTEM
from app.agents.state import AgentState
from app.agents.tools.investigation import run_investigation_tools
from app.agents.trace import append_trace
from app.schemas.agent import InvestigationResult


def investigate_context_node(state: AgentState, config: RunnableConfig) -> AgentState:
    context = require_context(state)
    configurable = (config or {}).get("configurable") or {}
    historical = configurable.get("historical_intelligence") or []
    used, results = run_investigation_tools(context, state=dict(state), historical=historical)
    trace = list(state.get("agent_trace") or [])
    seeded = {**state, "agent_trace": trace}
    for name in used:
        seeded["agent_trace"] = append_trace(
            seeded,
            agent="investigator",
            event_type="TOOL_CALL",
            summary=f"Called {name}",
            tool_name=name,
        )
        seeded["agent_trace"] = append_trace(
            seeded,
            agent="investigator",
            event_type="TOOL_RESULT",
            summary=f"Received {name}",
            tool_name=name,
        )

    investigation = fallback_investigation(context, tools_used=used, tool_results=results)
    used_llm = False
    llm = resolve_llm(config)
    if llm is not None:
        try:
            investigation = invoke_structured(
                llm,
                schema=InvestigationResult,
                system=INVESTIGATOR_SYSTEM,
                user=json.dumps({"tool_results": results, "tools_used": used}, default=str),
                schema_name="InvestigationResult",
                extra={"source": "llm", "tools_used": used},
            )
            used_llm = True
        except (LLMError, Exception):
            investigation = fallback_investigation(context, tools_used=used, tool_results=results)

    trail = append_audit(
        seeded,
        "investigate_context",
        "evidence_ready",
        investigation.evidence_summary,
        {"tools_used": used, "source": investigation.source},
    )
    trace = append_trace(
        {**seeded, "agent_trace": seeded.get("agent_trace") or []},
        agent="investigator",
        event_type="INVESTIGATION_COMPLETE",
        summary=investigation.evidence_summary,
        fallback_used=investigation.source != "llm",
    )
    return {
        "investigation": investigation.model_dump(mode="json"),
        "used_llm": bool(state.get("used_llm")) or used_llm,
        "audit_trail": trail,
        "agent_trace": trace,
    }
