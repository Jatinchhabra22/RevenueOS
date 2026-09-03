from fastapi import APIRouter, Depends, Query

from app.api.deps import get_runtime
from app.schemas.api import MetricsDashboardResponse, MetricsOverviewResponse
from app.schemas.outcomes import ActionEffectivenessResponse, OutcomeMetricsResponse, SegmentIntelligenceResponse
from app.services.dashboard import dashboard_metrics
from app.services.metrics import overview_metrics
from app.services.outcomes import action_effectiveness, aggregate_outcomes, load_outcome_records, segment_intelligence
from app.services.runtime import AppRuntime

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverviewResponse)
def metrics_overview(runtime: AppRuntime = Depends(get_runtime)) -> MetricsOverviewResponse:
    return overview_metrics(runtime)


@router.get("/dashboard", response_model=MetricsDashboardResponse)
def metrics_dashboard(runtime: AppRuntime = Depends(get_runtime)) -> MetricsDashboardResponse:
    return dashboard_metrics(runtime)


@router.get("/outcomes", response_model=OutcomeMetricsResponse)
def metrics_outcomes(runtime: AppRuntime = Depends(get_runtime)) -> OutcomeMetricsResponse:
    return aggregate_outcomes(load_outcome_records(runtime))


@router.get("/actions", response_model=ActionEffectivenessResponse)
def metrics_actions(
    action_type: str | None = Query(default=None),
    runtime: AppRuntime = Depends(get_runtime),
) -> ActionEffectivenessResponse:
    return action_effectiveness(load_outcome_records(runtime), action_type=action_type)


@router.get("/segments", response_model=SegmentIntelligenceResponse)
def metrics_segments(runtime: AppRuntime = Depends(get_runtime)) -> SegmentIntelligenceResponse:
    return segment_intelligence(load_outcome_records(runtime))
