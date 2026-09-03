from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit, parse_candidates
from app.agents.llm.extra_fallback import fallback_reflection
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.prompts import REFLECTION_SYSTEM
from app.agents.state import AgentState
from app.agents.trace import append_trace
from app.core.config import get_settings
from app.schemas.agent import ReflectionResult


def _has_alternative(state: AgentState) -> bool:
    selected = (state.get("selected_action") or {}).get("action_type")
    types = {item.action_type for item in parse_candidates(state) if item.action_type != "stop_recovery"}
    avoid = set(state.get("avoid_actions") or [])
    if selected:
        avoid.add(str(selected))
    return bool(types - avoid)


def reflect_outcome_node(state: AgentState, config: RunnableConfig) -> AgentState:
    outcome = str((state.get("outcome") or {}).get("outcome") or "NO_ACTION")
    action_type = str((state.get("selected_action") or {}).get("action_type") or "none")
    iteration = int(state.get("iteration") or 1)
    max_iterations = int(state.get("max_iterations") or get_settings().max_agent_iterations)
    has_alternative = _has_alternative(state)
    reflection = fallback_reflection(
        outcome=outcome,
        action_type=action_type,
        iteration=iteration,
        max_iterations=max_iterations,
        has_alternative=has_alternative,
    )
    used_llm = False
    llm = resolve_llm(config)
    if llm is not None:
        try:
            parsed = invoke_structured(
                llm,
                schema=ReflectionResult,
                system=REFLECTION_SYSTEM,
                user=json.dumps(
                    {
                        "outcome": state.get("outcome"),
                        "action": action_type,
                        "iteration": iteration,
                        "max_iterations": max_iterations,
                        "has_alternative": has_alternative,
                    },
                    default=str,
                ),
                schema_name="ReflectionResult",
                extra={"source": "llm"},
            )
            if outcome == "RECOVERED":
                parsed = parsed.model_copy(update={"recommended_next_step": "RECOVERED", "source": "llm"})
            reflection = parsed
            used_llm = True
        except (LLMError, Exception):
            reflection = fallback_reflection(
                outcome=outcome,
                action_type=action_type,
                iteration=iteration,
                max_iterations=max_iterations,
                has_alternative=has_alternative,
            )

    if iteration >= max_iterations and reflection.recommended_next_step == "CONTINUE":
        reflection = reflection.model_copy(update={"recommended_next_step": "STOP_RECOVERY"})

    trail = append_audit(
        state,
        "reflect_outcome",
        reflection.recommended_next_step,
        reflection.summary,
        {"source": reflection.source},
    )
    trace = append_trace(
        {**state, "agent_trace": state.get("agent_trace") or []},
        agent="reflection",
        event_type="REFLECTION_COMPLETE",
        summary=reflection.summary,
        decision=reflection.recommended_next_step,
        fallback_used=reflection.source != "llm",
    )
    return {
        "reflection": reflection.model_dump(mode="json"),
        "avoid_actions": list({*list(state.get("avoid_actions") or []), *reflection.avoid_actions}),
        "used_llm": bool(state.get("used_llm")) or used_llm,
        "audit_trail": trail,
        "agent_trace": trace,
        "next_step": "supervisor",
    }
