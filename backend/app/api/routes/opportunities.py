from fastapi import APIRouter, Depends, Query

from app.api.deps import get_runtime
from app.schemas.api import OpportunityListResponse, PriorityFilter
from app.services.opportunities import list_opportunities
from app.services.runtime import AppRuntime

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunityListResponse)
def get_opportunities(
    priority: PriorityFilter | None = Query(default=None),
    status: str = Query(default="open"),
    minimum_amount: float | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    runtime: AppRuntime = Depends(get_runtime),
) -> OpportunityListResponse:
    return list_opportunities(
        runtime,
        priority=priority,
        status=status,
        minimum_amount=minimum_amount,
        limit=limit,
        offset=offset,
    )
