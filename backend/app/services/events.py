"""Event detail orchestration: context + predictions + risk, no agent run."""

from __future__ import annotations

from app.core.errors import APIError
from app.schemas.api import EventDetailResponse
from app.services.data.context import assemble_event_context
from app.services.prediction.inference import predict_churn, predict_recovery
from app.services.recoverability import classify_recoverability
from app.services.risk.engine import assess_revenue_risk
from app.services.runtime import AppRuntime


def get_event_detail(runtime: AppRuntime, event_id: str) -> EventDetailResponse:
    tables = runtime.tables()
    try:
        context = assemble_event_context(event_id, tables)
    except ValueError as exc:
        if "Unknown event_id" in str(exc):
            raise APIError("EVENT_NOT_FOUND", f"Revenue event {event_id} was not found.", status_code=404) from exc
        raise APIError("EVENT_NOT_FOUND", str(exc), status_code=404) from exc

    recovery = predict_recovery(context, runtime.artifacts_dir)
    churn = predict_churn(context, runtime.artifacts_dir)
    risk = assess_revenue_risk(context, recovery, churn)
    recoverability = classify_recoverability(context, recovery, churn, risk)
    return EventDetailResponse(
        event=context.event,
        customer=context.customer,
        subscription=context.subscription,
        related_transaction=context.related_transaction,
        recent_transactions=context.recent_transactions,
        previous_interventions=context.previous_interventions,
        recovery_prediction=recovery,
        churn_prediction=churn,
        risk_assessment=risk,
        recoverability=recoverability,
        status=context.event.event_status,
    )
