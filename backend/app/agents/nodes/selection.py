import json

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit, optional_churn, optional_recovery, parse_candidates, require_context
from app.agents.llm.fallback import annotate_decision_with_history, fallback_select_action
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.state import AgentState
from app.schemas.agent import ActionDecision
from app.schemas.risk import RiskAssessment
from app.services.recoverability import classify_recoverability
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.state import AgentState
from app.schemas.agent import ActionDecision
from app.schemas.risk import RiskAssessment


def select_action_node(state: AgentState, config: RunnableConfig) -> AgentState:
    context = require_context(state)
    candidates = parse_candidates(state)
    if not candidates:
        raise ValueError("select_action requires candidate_actions")
    recovery = optional_recovery(state)
    churn = optional_churn(state)
    risk = RiskAssessment.model_validate(state["risk_assessment"]) if state.get("risk_assessment") else None
    llm = resolve_llm(config)
    configurable = (config or {}).get("configurable") or {}
    historical = configurable.get("historical_intelligence") or []
    segment = context.event.failure_reason

    avoid = list(state.get("avoid_actions") or [])
    decision = fallback_select_action(
        candidates,
        context,
        recovery,
        churn,
        risk,
        historical=historical,
        avoid_types=avoid,
    )
    used_llm = False
    if llm is not None:
        try:
            parsed = invoke_structured(
                llm,
                schema=ActionDecision,
                system=(
                    "Select exactly one candidate action. selected_action_id MUST be one of the supplied IDs. "
                    "Do not invent actions or probabilities. Historical effectiveness is contextual evidence only "
                    "and must not invent new actions. Return JSON."
                ),
                user=json.dumps(
                    {
                        "candidates": [item.model_dump() for item in candidates],
                        "diagnosis": state.get("diagnosis"),
                        "customer_analysis": state.get("customer_analysis"),
                        "recovery_probability": recovery.probability if recovery else None,
                        "churn_probability": churn.probability if churn else None,
                        "risk": risk.model_dump() if risk else None,
                        "historical_effectiveness": historical,
                        "avoid_actions": avoid,
                    },
                    default=str,
                ),
                schema_name="ActionDecision",
                extra={"source": "llm"},
            )
            valid_ids = {item.action_id for item in candidates}
            if parsed.selected_action_id not in valid_ids:
                raise LLMError("selected_action_id is not a candidate")
            chosen = next(item for item in candidates if item.action_id == parsed.selected_action_id)
            if chosen.action_type in avoid and any(item.action_type not in avoid for item in candidates):
                raise LLMError("selected action is in the avoid list")
            decision = parsed.model_copy(update={"selected_action_type": chosen.action_type, "source": "llm"})
            decision = annotate_decision_with_history(
                decision,
                action_type=chosen.action_type,
                segment=segment,
                historical=historical,
            )
            used_llm = True
        except (LLMError, Exception):
            decision = fallback_select_action(
                candidates,
                context,
                recovery,
                churn,
                risk,
                historical=historical,
                avoid_types=avoid,
            )

    chosen_action = next(item for item in candidates if item.action_id == decision.selected_action_id)
    recoverability = classify_recoverability(context, recovery, churn, risk)
    economic_stop = recoverability.classification in {
        "NOT_RECOVERABLE",
        "LOW_RECOVERABILITY",
        "NEEDS_REVIEW",
    }
    if not recoverability.pursue and economic_stop:
        stop = next((item for item in candidates if item.action_type == "stop_recovery"), None)
        if stop is not None and chosen_action.action_type != "stop_recovery":
            alternative = chosen_action.action_type
            decision = ActionDecision(
                selected_action_id=stop.action_id,
                selected_action_type=stop.action_type,
                reason=recoverability.reason,
                confidence=0.72,
                alternative_considered=alternative,
                source="fallback",
            )
            chosen_action = stop
    alternative = decision.alternative_considered
    strategy = {
        "recommended_action": chosen_action.action_type,
        "alternative_action": alternative,
        "reasoning_summary": decision.reason,
        "expected_effect": chosen_action.expected_effect,
        "customer_impact": f"Friction {chosen_action.friction}",
        "confidence": decision.confidence,
        "source": decision.source,
    }
    trail = append_audit(
        state,
        "select_action",
        decision.selected_action_type,
        decision.reason,
        {"source": decision.source, "confidence": decision.confidence, "informed_by_observations": decision.informed_by_observations},
    )
    trace_state = {**state, "agent_trace": state.get("agent_trace") or []}
    from app.agents.trace import append_trace

    trace = append_trace(
        trace_state,
        agent="strategist",
        event_type="STRATEGY_COMPLETE",
        summary=decision.reason,
        decision=chosen_action.action_type,
        fallback_used=decision.source != "llm",
    )
    return {
        "decision": decision.model_dump(mode="json"),
        "selected_action": chosen_action.model_dump(mode="json"),
        "strategy": strategy,
        "used_llm": bool(state.get("used_llm")) or used_llm,
        "audit_trail": trail,
        "agent_trace": trace,
        "recoverability": recoverability.model_dump(mode="json"),
    }
