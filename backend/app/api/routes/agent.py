from fastapi import APIRouter, Body, Depends

from app.api.deps import get_runtime
from app.schemas.api import AgentActivityResponse, AgentRunRequest, AgentWorkflowResponse
from app.services.agent_runs import get_latest_workflow, get_workflow_by_id, list_agent_activity, run_event_agent
from app.services.runtime import AppRuntime

router = APIRouter(tags=["agent"])


@router.get("/agent/activity", response_model=AgentActivityResponse)
def agent_activity(runtime: AppRuntime = Depends(get_runtime)) -> AgentActivityResponse:
    return list_agent_activity(runtime)


@router.post("/events/{event_id}/agent/run", response_model=AgentWorkflowResponse)
def run_agent(
    event_id: str,
    payload: AgentRunRequest | None = Body(default=None),
    runtime: AppRuntime = Depends(get_runtime),
) -> AgentWorkflowResponse:
    return run_event_agent(runtime, event_id, payload or AgentRunRequest())


@router.get("/events/{event_id}/agent/latest", response_model=AgentWorkflowResponse)
def latest_agent(event_id: str, runtime: AppRuntime = Depends(get_runtime)) -> AgentWorkflowResponse:
    return get_latest_workflow(runtime, event_id)


@router.get("/events/{event_id}/agent/{workflow_id}", response_model=AgentWorkflowResponse)
def workflow_by_id(
    event_id: str,
    workflow_id: str,
    runtime: AppRuntime = Depends(get_runtime),
) -> AgentWorkflowResponse:
    return get_workflow_by_id(runtime, event_id, workflow_id)
