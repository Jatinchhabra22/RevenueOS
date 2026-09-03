"""Compile and run the bounded recovery LangGraph."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.llm.provider import resolve_llm
from app.agents.llm.runtime import describe_runtime
from app.agents.llm.tracing import TracingLLM
from app.agents.nodes.actions import generate_candidate_actions_node
from app.agents.nodes.context import assemble_context_node
from app.agents.nodes.customer import analyze_customer_node
from app.agents.nodes.diagnosis import diagnose_event_node
from app.agents.nodes.execution import execute_action_node
from app.agents.nodes.finalize import finalize_node
from app.agents.nodes.guardrails import validate_guardrails_node
from app.agents.nodes.investigate import investigate_context_node
from app.agents.nodes.monitoring import monitor_result_node
from app.agents.nodes.predictions import get_predictions_node
from app.agents.nodes.reflect import reflect_outcome_node
from app.agents.nodes.risk import assess_revenue_risk_node
from app.agents.nodes.routing import route_after_guardrails, route_next_step_node
from app.agents.nodes.selection import select_action_node
from app.agents.nodes.supervisor import route_supervisor, supervisor_node
from app.agents.state import AgentState
from app.core.config import get_settings
from app.schemas.entities import EventContext

_UNSET = object()


def build_recovery_graph():
    graph = StateGraph(AgentState)
    graph.add_node("assemble_context", assemble_context_node)
    graph.add_node("get_predictions", get_predictions_node)
    graph.add_node("assess_revenue_risk", assess_revenue_risk_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("investigate_context", investigate_context_node)
    graph.add_node("diagnose_event", diagnose_event_node)
    graph.add_node("analyze_customer", analyze_customer_node)
    graph.add_node("generate_candidate_actions", generate_candidate_actions_node)
    graph.add_node("select_action", select_action_node)
    graph.add_node("validate_guardrails", validate_guardrails_node)
    graph.add_node("route_next_step", route_next_step_node)
    graph.add_node("execute_action", execute_action_node)
    graph.add_node("monitor_result", monitor_result_node)
    graph.add_node("reflect_outcome", reflect_outcome_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "assemble_context")
    graph.add_edge("assemble_context", "get_predictions")
    graph.add_edge("get_predictions", "assess_revenue_risk")
    graph.add_edge("assess_revenue_risk", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "investigate_context": "investigate_context",
            "diagnose_event": "diagnose_event",
            "analyze_customer": "analyze_customer",
            "generate_candidate_actions": "generate_candidate_actions",
            "finalize": "finalize",
        },
    )
    graph.add_edge("investigate_context", "diagnose_event")
    graph.add_edge("diagnose_event", "analyze_customer")
    graph.add_edge("analyze_customer", "generate_candidate_actions")
    graph.add_edge("generate_candidate_actions", "select_action")
    graph.add_edge("select_action", "validate_guardrails")
    graph.add_edge("validate_guardrails", "route_next_step")
    graph.add_conditional_edges(
        "route_next_step",
        route_after_guardrails,
        {
            "execute_action": "execute_action",
            "finalize": "finalize",
        },
    )
    graph.add_edge("execute_action", "monitor_result")
    graph.add_edge("monitor_result", "reflect_outcome")
    graph.add_edge("reflect_outcome", "supervisor")
    graph.add_edge("finalize", END)
    return graph.compile()


_COMPILED = None


def get_compiled_graph():
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_recovery_graph()
    return _COMPILED


def reset_compiled_graph() -> None:
    global _COMPILED
    _COMPILED = None


def run_recovery_agent(
    *,
    event_id: str | None = None,
    context: EventContext | None = None,
    tables: dict | None = None,
    artifacts_dir: Path | None = None,
    llm: Any = _UNSET,
    recovery_prediction: dict | None = None,
    churn_prediction: dict | None = None,
    risk_assessment: dict | None = None,
    historical_intelligence: list | None = None,
) -> AgentState:
    if context is None and not event_id:
        raise ValueError("run_recovery_agent requires event_id or context")
    settings = get_settings()
    payload: AgentState = {
        "audit_trail": [],
        "agent_trace": [],
        "iteration_history": [],
        "iteration": 0,
        "used_llm": False,
        "max_iterations": settings.max_agent_iterations,
    }
    if event_id:
        payload["event_id"] = event_id
    if context is not None:
        payload["event_context"] = context.model_dump(mode="json")
        payload["event_id"] = context.event.event_id
        payload["customer_id"] = context.event.customer_id
    if recovery_prediction:
        payload["recovery_prediction"] = recovery_prediction
    if churn_prediction:
        payload["churn_prediction"] = churn_prediction
    if risk_assessment:
        payload["risk_assessment"] = risk_assessment

    configurable: dict[str, Any] = {
        "tables": tables,
        "artifacts_dir": str(artifacts_dir) if artifacts_dir else None,
    }
    if llm is not _UNSET:
        configurable["llm"] = llm
    if historical_intelligence:
        configurable["historical_intelligence"] = historical_intelligence

    records: list[dict[str, Any]] = []
    resolved = resolve_llm({"configurable": configurable})
    meta = describe_runtime(resolved, injected=llm is not _UNSET and llm is not None)
    payload["agent_mode"] = str(meta.get("agent_mode") or "deterministic_fallback")
    payload["provider"] = meta.get("provider")
    payload["model"] = meta.get("model")
    payload["fallback_used"] = bool(meta.get("fallback_used"))
    if resolved is not None:
        configurable["llm"] = TracingLLM(resolved, records)

    config = {"configurable": configurable, "recursion_limit": 80}
    state = get_compiled_graph().invoke(payload, config=config)
    return _apply_runtime_evidence(dict(state), meta=meta, llm_records=records)


def _apply_runtime_evidence(state: dict[str, Any], *, meta: dict[str, Any], llm_records: list[dict[str, Any]]) -> AgentState:
    from app.agents.audit import utcnow
    from app.schemas.agent import AgentTraceEvent

    trail = list(state.get("agent_trace") or [])
    for rec in llm_records:
        trail.append(
            AgentTraceEvent(
                trace_id=f"LLM_{rec.get('schema_name', 'call')}_{len(trail)}",
                workflow_id=str(state.get("workflow_id") or ""),
                iteration=int(state.get("iteration") or 1),
                agent=str(rec.get("agent") or "llm"),
                event_type=str(rec.get("event_type") or "LLM_CALL"),
                timestamp=utcnow(),
                status="ok" if rec.get("success", rec.get("event_type") == "LLM_CALL_STARTED") else "error",
                summary=str(rec.get("schema_name") or "structured"),
                fallback_used=rec.get("success") is False,
                duration_ms=rec.get("duration_ms"),
            ).model_dump(mode="json")
        )
    used = bool(state.get("used_llm"))
    completed = [item for item in llm_records if item.get("event_type") == "LLM_CALL_COMPLETED" and item.get("success")]
    if used and meta.get("provider") == "ollama":
        state["agent_mode"] = "ollama"
        state["provider"] = "ollama"
        state["model"] = meta.get("model")
        state["fallback_used"] = False
    elif used:
        state["fallback_used"] = False
        if meta.get("provider"):
            state["provider"] = meta.get("provider")
            state["model"] = meta.get("model")
    else:
        state["fallback_used"] = True
        state["agent_mode"] = "deterministic_fallback"
    state["agent_trace"] = trail
    state["llm_calls"] = llm_records
    state["llm_call_count"] = len(completed)
    return state  # type: ignore[return-value]
