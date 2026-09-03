from fastapi import APIRouter, Depends

from app.api.deps import get_runtime
from app.schemas.api import CopilotAskRequest, CopilotAskResponse
from app.services.copilot import ask_copilot
from app.services.runtime import AppRuntime

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/ask", response_model=CopilotAskResponse)
def copilot_ask(payload: CopilotAskRequest, runtime: AppRuntime = Depends(get_runtime)) -> CopilotAskResponse:
    return ask_copilot(runtime, event_id=payload.event_id, question=payload.question)
