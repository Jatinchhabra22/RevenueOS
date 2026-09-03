"""Run and persist bounded recovery workflows."""

from __future__ import annotations

from pathlib import Path
import json

from app.agents.graph import run_recovery_agent
from app.core.errors import APIError
from app.schemas.api import AgentActivityResponse, AgentRunRequest, AgentWorkflowResponse
from app.schemas.entities import EventContext
from app.services.data.context import assemble_event_context
from app.services.outcomes import (
    historical_intelligence_for_context,
    list_persisted_activity,
    load_outcome_records,
    outcome_context_payload,
    simulated_interventions_for_event,
)
from app.services.persistence import append_jsonl, read_json, write_json_atomic
from app.services.prediction.inference import predict_churn, predict_recovery
from app.services.risk.engine import assess_revenue_risk
from app.services.runtime import AppRuntime


def _latest_path(runtime: AppRuntime, event_id: str) -> Path:
    return runtime.workflows_dir / event_id / "latest.json"


def _history_path(runtime: AppRuntime, event_id: str) -> Path:
    return runtime.workflows_dir / event_id / "history.jsonl"


def _to_response(state: dict, *, dry_run: bool) -> AgentWorkflowResponse:
    try:
        history = state.get("iteration_history") or []
        iterations = max(int(state.get("iteration") or 1), len(history) or 1)
        strategy = state.get("strategy")
        return AgentWorkflowResponse(
            workflow_id=str(state.get("workflow_id") or ""),
            event_id=str(state.get("event_id") or ""),
            diagnosis=state["diagnosis"],
            recovery_prediction=state["recovery_prediction"],
            churn_prediction=state["churn_prediction"],
            risk_assessment=state["risk_assessment"],
            candidate_actions=state.get("candidate_actions") or [],
            selected_action=state["selected_action"],
            decision=state["decision"],
            guardrail_result=state["guardrail_result"],
            execution_result=state.get("tool_result"),
            outcome=state.get("outcome"),
            final_decision=str(state.get("status") or "completed"),
            status=str(state.get("status") or "completed"),
            used_llm=bool(state.get("used_llm")),
            dry_run=dry_run,
            audit_trail=state.get("audit_trail") or [],
            agent_mode=str(state.get("agent_mode") or "deterministic_fallback"),
            provider=state.get("provider"),
            model=state.get("model"),
            fallback_used=bool(state.get("fallback_used", not state.get("used_llm"))),
            iterations=iterations,
            current_stage=str(state.get("next_step") or "END"),
            workflow_status=state.get("workflow_status") or state.get("status"),
            terminal_reason=state.get("terminal_reason"),
            investigation=state.get("investigation"),
            customer_analysis=state.get("customer_analysis"),
            strategy=strategy,
            reflection=state.get("reflection"),
            agent_trace=state.get("agent_trace") or [],
            iteration_history=list(history),
            llm_call_count=int(state.get("llm_call_count") or 0),
            recoverability=state.get("recoverability"),
        )
    except Exception as exc:
        raise APIError(
            "AGENT_EXECUTION_FAILED",
            "The agent finished but the result could not be serialized.",
            status_code=500,
        ) from exc


def persist_workflow(runtime: AppRuntime, result: AgentWorkflowResponse, context: EventContext | None = None) -> None:
    payload = result.model_dump(mode="json")
    if context is not None:
        payload["outcome_context"] = outcome_context_payload(context)
    write_json_atomic(_latest_path(runtime, result.event_id), payload)
    append_jsonl(_history_path(runtime, result.event_id), payload)


def get_latest_workflow(runtime: AppRuntime, event_id: str) -> AgentWorkflowResponse:
    path = _latest_path(runtime, event_id)
    if not path.exists():
        raise APIError(
            "WORKFLOW_NOT_FOUND",
            f"No agent workflow was found for revenue event {event_id}.",
            status_code=404,
        )
    try:
        return AgentWorkflowResponse.model_validate(read_json(path))
    except APIError:
        raise
    except Exception as exc:
        raise APIError(
            "WORKFLOW_CORRUPT",
            "The stored workflow for this event could not be read.",
            status_code=422,
        ) from exc


def get_workflow_by_id(runtime: AppRuntime, event_id: str, workflow_id: str) -> AgentWorkflowResponse:
    path = _history_path(runtime, event_id)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(payload.get("workflow_id") or "") == workflow_id:
                try:
                    return AgentWorkflowResponse.model_validate(payload)
                except Exception as exc:
                    raise APIError(
                        "WORKFLOW_CORRUPT",
                        "The stored workflow for this event could not be read.",
                        status_code=422,
                    ) from exc
    latest = get_latest_workflow(runtime, event_id)
    if latest.workflow_id == workflow_id:
        return latest
    raise APIError(
        "WORKFLOW_NOT_FOUND",
        f"Workflow {workflow_id} was not found for revenue event {event_id}.",
        status_code=404,
    )


def list_agent_activity(runtime: AppRuntime) -> AgentActivityResponse:
    return list_persisted_activity(runtime)


def run_event_agent(runtime: AppRuntime, event_id: str, request: AgentRunRequest) -> AgentWorkflowResponse:
    tables = runtime.tables()
    try:
        context = assemble_event_context(event_id, tables)
    except ValueError as exc:
        if "Unknown event_id" in str(exc):
            raise APIError("EVENT_NOT_FOUND", f"Revenue event {event_id} was not found.", status_code=404) from exc
        raise APIError("EVENT_NOT_FOUND", str(exc), status_code=404) from exc

    simulated = simulated_interventions_for_event(runtime, event_id)
    if simulated:
        context = context.model_copy(
            update={"previous_interventions": list(context.previous_interventions) + simulated}
        )

    extras: dict = {}
    if request.force_recompute:
        recovery = predict_recovery(context, runtime.artifacts_dir)
        churn = predict_churn(context, runtime.artifacts_dir)
        extras["recovery_prediction"] = recovery.model_dump(mode="json")
        extras["churn_prediction"] = churn.model_dump(mode="json")
        extras["risk_assessment"] = assess_revenue_risk(context, recovery, churn).model_dump(mode="json")

    try:
        kwargs: dict = {
            "event_id": event_id,
            "context": context,
            "tables": tables,
            "artifacts_dir": runtime.artifacts_dir,
            **extras,
        }
        if runtime.disable_llm:
            kwargs["llm"] = None
        records = load_outcome_records(runtime)
        signals = historical_intelligence_for_context(records, failure_reason=context.event.failure_reason)
        if signals:
            kwargs["historical_intelligence"] = [item.model_dump(mode="json") for item in signals]
        state = run_recovery_agent(**kwargs)
    except APIError:
        raise
    except Exception as exc:
        raise APIError(
            "AGENT_EXECUTION_FAILED",
            "The recovery agent failed while processing this event.",
            status_code=500,
        ) from exc

    result = _to_response(dict(state), dry_run=request.dry_run)
    if not request.dry_run:
        persist_workflow(runtime, result, context=context)
    return result
