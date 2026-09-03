from fastapi import APIRouter

from app.agents.llm.runtime import agent_health_payload
from app.core.constants import HEALTHY_STATUS, SERVICE_NAME
from app.schemas.health import AgentHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status=HEALTHY_STATUS, service=SERVICE_NAME)


@router.get("/agent/health", response_model=AgentHealthResponse)
def agent_health() -> AgentHealthResponse:
    return AgentHealthResponse.model_validate(agent_health_payload())
