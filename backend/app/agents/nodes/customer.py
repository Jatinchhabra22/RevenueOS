from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit, optional_churn, require_context
from app.agents.llm.extra_fallback import fallback_customer_analysis
from app.agents.llm.provider import LLMError, resolve_llm
from app.agents.llm.structured import invoke_structured
from app.agents.prompts import CUSTOMER_SYSTEM
from app.agents.state import AgentState
from app.agents.trace import append_trace
from app.schemas.agent import CustomerAnalysis


def analyze_customer_node(state: AgentState, config: RunnableConfig) -> AgentState:
    context = require_context(state)
    churn = optional_churn(state)
    raw_churn = (state.get("churn_prediction") or {}).get("probability")
    analysis = fallback_customer_analysis(context, churn)
    used_llm = False
    llm = resolve_llm(config)
    if llm is not None:
        try:
            parsed = invoke_structured(
                llm,
                schema=CustomerAnalysis,
                system=CUSTOMER_SYSTEM,
                user=json.dumps(
                    {
                        "customer": context.customer.model_dump(mode="json") if context.customer else None,
                        "ml_churn_probability": raw_churn,
                        "investigation": state.get("investigation"),
                    },
                    default=str,
                ),
                schema_name="CustomerAnalysis",
                extra={"source": "llm", "ml_churn_probability": raw_churn},
            )
            analysis = parsed.model_copy(update={"ml_churn_probability": raw_churn, "source": "llm"})
            used_llm = True
        except (LLMError, Exception):
            analysis = fallback_customer_analysis(context, churn)

    trail = append_audit(
        state,
        "analyze_customer",
        analysis.churn_risk,
        analysis.summary,
        {"source": analysis.source},
    )
    trace = append_trace(
        {**state, "agent_trace": state.get("agent_trace") or []},
        agent="customer_analyst",
        event_type="CUSTOMER_ANALYSIS_COMPLETE",
        summary=analysis.summary,
        fallback_used=analysis.source != "llm",
    )
    return {
        "customer_analysis": analysis.model_dump(mode="json"),
        "used_llm": bool(state.get("used_llm")) or used_llm,
        "audit_trail": trail,
        "agent_trace": trace,
    }
