from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit
from app.agents.llm.extra_fallback import fallback_supervisor
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.memory import merge_executed_intervention, snapshot_iteration
from app.agents.prompts import SUPERVISOR_SYSTEM
from app.agents.state import AgentState
from app.agents.trace import append_trace
from app.core.config import get_settings
from app.schemas.agent import ReflectionResult, SupervisorDecision

_ALLOWED = {
    "INVESTIGATE",
    "DIAGNOSE",
    "ANALYZE_CUSTOMER",
    "STRATEGIZE",
    "WAIT_FOR_CUSTOMER",
    "ESCALATE_TO_MERCHANT",
    "STOP_RECOVERY",
    "RECOVERED",
}


def _missing(state: AgentState) -> str | None:
    if not state.get("investigation"):
        return "investigation"
    if not state.get("diagnosis"):
        return "diagnosis"
    if not state.get("customer_analysis"):
        return "customer"
    return None


def _sanitize(route: str, state: AgentState, reflection: ReflectionResult | None) -> str:
    missing = _missing(state)
    if missing == "investigation":
        return "INVESTIGATE"
    if missing == "diagnosis":
        return "DIAGNOSE"
    if missing == "customer" and route != "INVESTIGATE":
        return "ANALYZE_CUSTOMER"
    if route in {"EXECUTE", "VALIDATE", "OBSERVE"}:
        return "STRATEGIZE"
    if route not in _ALLOWED:
        return "STOP_RECOVERY"
    if reflection and reflection.recommended_next_step != "CONTINUE" and route == "STRATEGIZE":
        mapped = {
            "WAIT_FOR_CUSTOMER": "WAIT_FOR_CUSTOMER",
            "ESCALATE_TO_MERCHANT": "ESCALATE_TO_MERCHANT",
            "STOP_RECOVERY": "STOP_RECOVERY",
            "RECOVERED": "RECOVERED",
        }.get(reflection.recommended_next_step)
        if mapped:
            return mapped
    return route


def supervisor_node(state: AgentState, config: RunnableConfig) -> AgentState:
    missing = _missing(state)
    recovered = str((state.get("outcome") or {}).get("outcome") or "") == "RECOVERED"
    reflection = None
    if state.get("reflection"):
        reflection = ReflectionResult.model_validate(state["reflection"])
    decision = fallback_supervisor(missing=missing, reflection=reflection, recovered=recovered)
    used_llm = False
    llm = resolve_llm(config)
    if llm is not None:
        try:
            parsed = invoke_structured(
                llm,
                schema=SupervisorDecision,
                system=SUPERVISOR_SYSTEM,
                user=json.dumps(
                    {
                        "iteration": state.get("iteration"),
                        "outcome": state.get("outcome"),
                        "reflection": state.get("reflection"),
                        "missing": missing,
                    },
                    default=str,
                ),
                schema_name="SupervisorDecision",
                extra={"source": "llm"},
            )
            decision = parsed
            used_llm = True
        except (LLMError, Exception):
            decision = fallback_supervisor(missing=missing, reflection=reflection, recovered=recovered)

    route = _sanitize(str(decision.route), state, reflection)
    iteration = int(state.get("iteration") or 1)
    max_iterations = int(state.get("max_iterations") or get_settings().max_agent_iterations)
    updates: AgentState = {}
    history = list(state.get("iteration_history") or [])
    if reflection is not None:
        history.append(snapshot_iteration(state))
        updates["iteration_history"] = history
        if route == "STRATEGIZE":
            if iteration >= max_iterations:
                route = "STOP_RECOVERY"
            else:
                updates["event_context"] = merge_executed_intervention(state)
                updates["iteration"] = iteration + 1

    terminal = {
        "WAIT_FOR_CUSTOMER": ("waiting", "WAIT_FOR_CUSTOMER"),
        "ESCALATE_TO_MERCHANT": ("escalated", "ESCALATE_TO_MERCHANT"),
        "STOP_RECOVERY": (state.get("status") or "completed", "STOP_RECOVERY"),
        "RECOVERED": ("completed", "RECOVERED"),
    }
    next_step = "finalize" if route in terminal else {
        "INVESTIGATE": "investigate_context",
        "DIAGNOSE": "diagnose_event",
        "ANALYZE_CUSTOMER": "analyze_customer",
        "STRATEGIZE": "generate_candidate_actions",
    }.get(route, "finalize")

    if route in terminal:
        status, reason = terminal[route]
        if route == "STOP_RECOVERY" and (state.get("outcome") or {}).get("outcome") == "NO_ACTION":
            status = "no_action"
        updates["status"] = status
        updates["workflow_status"] = reason
        updates["terminal_reason"] = reason

    trail = append_audit(state, "supervisor", route, decision.reason, {"source": decision.source})
    trace = append_trace(
        {**state, "agent_trace": state.get("agent_trace") or []},
        agent="supervisor",
        event_type="SUPERVISOR_DECISION",
        summary=decision.reason,
        decision=route,
        fallback_used=decision.source != "llm",
    )
    updates.update(
        {
            "supervisor_route": route,
            "next_step": next_step,
            "used_llm": bool(state.get("used_llm")) or used_llm,
            "audit_trail": trail,
            "agent_trace": trace,
        }
    )
    return updates


def route_supervisor(state: AgentState) -> str:
    nxt = str(state.get("next_step") or "finalize")
    allowed = {
        "investigate_context",
        "diagnose_event",
        "analyze_customer",
        "generate_candidate_actions",
        "finalize",
    }
    return nxt if nxt in allowed else "finalize"
