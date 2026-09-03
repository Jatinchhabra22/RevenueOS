import json

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit, require_context
from app.agents.llm.fallback import fallback_diagnosis
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.state import AgentState
from app.schemas.agent import Diagnosis
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction


def diagnose_event_node(state: AgentState, config: RunnableConfig) -> AgentState:
    context = require_context(state)
    recovery = (
        RecoveryPrediction.model_validate(state["recovery_prediction"])
        if state.get("recovery_prediction")
        else None
    )
    churn = (
        ChurnPrediction.model_validate(state["churn_prediction"])
        if state.get("churn_prediction")
        else None
    )
    llm = resolve_llm(config)

    source = "fallback"
    used_llm = False
    diagnosis = fallback_diagnosis(context, recovery, churn)
    if llm is not None:
        try:
            diagnosis = invoke_structured(
                llm,
                schema=Diagnosis,
                system=(
                    "You diagnose payment recovery events. Use only supplied facts. "
                    "Do not invent probabilities, customers, or actions. Return JSON."
                ),
                user=json.dumps(
                    {
                        "event": context.event.model_dump(mode="json"),
                        "customer": context.customer.model_dump(mode="json") if context.customer else None,
                        "investigation": state.get("investigation"),
                    },
                    default=str,
                ),
                schema_name="Diagnosis",
                extra={"source": "llm"},
            )
            source = "llm"
            used_llm = True
        except (LLMError, Exception):
            diagnosis = fallback_diagnosis(context, recovery, churn)

    trail = append_audit(
        state,
        "diagnose_event",
        diagnosis.issue_category,
        diagnosis.primary_issue,
        {"source": source},
    )
    from app.agents.trace import append_trace

    trace = append_trace(
        {**state, "agent_trace": state.get("agent_trace") or []},
        agent="diagnosis",
        event_type="DIAGNOSIS_COMPLETE",
        summary=diagnosis.primary_issue,
        fallback_used=source != "llm",
    )
    return {
        "diagnosis": diagnosis.model_dump(mode="json"),
        "used_llm": bool(state.get("used_llm")) or used_llm,
        "audit_trail": trail,
        "agent_trace": trace,
    }
