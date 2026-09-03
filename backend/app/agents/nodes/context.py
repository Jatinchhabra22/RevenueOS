import uuid

from langchain_core.runnables import RunnableConfig

from app.agents.audit import append_audit
from app.agents.state import AgentState
from app.schemas.entities import EventContext
from app.services.data.context import assemble_event_context


def _configurable(config: RunnableConfig | None) -> dict:
    return dict((config or {}).get("configurable") or {})


def assemble_context_node(state: AgentState, config: RunnableConfig) -> AgentState:
    if state.get("event_context"):
        context = EventContext.model_validate(state["event_context"])
        source = "provided"
    else:
        event_id = state.get("event_id")
        tables = _configurable(config).get("tables")
        if not event_id:
            raise ValueError("assemble_context requires event_id or event_context")
        if tables is None:
            raise ValueError("assemble_context requires config.configurable.tables when event_context is absent")
        context = assemble_event_context(str(event_id), tables)
        source = "tables"

    workflow_id = state.get("workflow_id") or f"WF_{uuid.uuid4().hex[:10]}"
    from app.core.config import get_settings

    seeded = {**state, "audit_trail": state.get("audit_trail") or []}
    trail = append_audit(
        seeded,
        "assemble_context",
        "context_ready",
        f"Event {context.event.event_id} context assembled from {source}.",
        {"event_id": context.event.event_id},
    )
    return {
        "workflow_id": workflow_id,
        "thread_id": workflow_id,
        "event_id": context.event.event_id,
        "customer_id": context.event.customer_id,
        "event_context": context.model_dump(mode="json"),
        "status": "started",
        "iteration": int(state.get("iteration") or 0) + 1,
        "max_iterations": int(state.get("max_iterations") or get_settings().max_agent_iterations),
        "audit_trail": trail,
    }
