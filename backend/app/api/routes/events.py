from fastapi import APIRouter, Depends

from app.api.deps import get_runtime
from app.schemas.api import EventDetailResponse
from app.services.events import get_event_detail
from app.services.runtime import AppRuntime

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/{event_id}", response_model=EventDetailResponse)
def event_detail(event_id: str, runtime: AppRuntime = Depends(get_runtime)) -> EventDetailResponse:
    return get_event_detail(runtime, event_id)
