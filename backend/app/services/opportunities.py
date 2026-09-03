"""Ranked recovery queue for the dashboard. Delegates scoring to Phase 5."""

from __future__ import annotations

import pandas as pd

from app.core.errors import APIError
from app.schemas.api import OpportunityItem, OpportunityListResponse, PriorityFilter
from app.schemas.risk import RiskAssessment
from app.services.recoverability import classify_recoverability
from app.services.risk.batch import score_events
from app.services.runtime import AppRuntime


def _event_lookup(events: pd.DataFrame) -> dict[str, dict]:
    if events.empty:
        return {}
    cleaned: dict[str, dict] = {}
    for row in events.to_dict(orient="records"):
        payload = {}
        for key, value in row.items():
            if value is None:
                payload[key] = None
            else:
                try:
                    payload[key] = None if pd.isna(value) else value
                except (TypeError, ValueError):
                    payload[key] = value
        cleaned[str(row["event_id"])] = payload
    return cleaned


def _to_item(assessment: RiskAssessment, event_row: dict | None, context=None) -> OpportunityItem:
    row = event_row or {}
    recoverability = None
    if context is not None:
        from app.schemas.predictions import ChurnPrediction, RecoveryPrediction

        recovery = RecoveryPrediction(
            probability=assessment.recovery_probability,
            recoverability="medium",
            model_type="risk",
            model_version="n/a",
        )
        churn = ChurnPrediction(
            probability=assessment.churn_probability,
            risk_category="medium",
            model_type="risk",
            model_version="n/a",
        )
        recoverability = classify_recoverability(context, recovery, churn, assessment)
    return OpportunityItem(
        event_id=assessment.event_id,
        customer_id=assessment.customer_id,
        amount_at_risk=assessment.amount_at_risk,
        recovery_probability=assessment.recovery_probability,
        churn_probability=assessment.churn_probability,
        expected_recovery_value=assessment.expected_recovery_value,
        priority_score=assessment.priority_score,
        priority_category=assessment.priority_category,
        failure_reason=row.get("failure_reason"),
        payment_method=row.get("payment_method"),
        event_type=row.get("event_type"),
        urgency=row.get("urgency") or assessment.urgency,
        customer_ltv=assessment.customer_ltv,
        status=row.get("event_status"),
        recoverability=recoverability.classification if recoverability else None,
        pursue=recoverability.pursue if recoverability else None,
    )


def scored_opportunities(runtime: AppRuntime, status: str = "open") -> list[OpportunityItem]:
    tables = runtime.tables()
    cache_key = f"{status}:{runtime._fingerprint()}"
    cached = runtime._opportunity_cache.get(cache_key)
    if cached is not None:
        return cached

    status_filter = "open" if status.lower() == "open" else "all"
    assessments = score_events(
        tables,
        status_filter=status_filter,  # type: ignore[arg-type]
        artifacts_dir=runtime.artifacts_dir,
    )
    lookup = _event_lookup(tables.get("revenue_events", pd.DataFrame()))
    from app.services.data.context import assemble_event_context

    items: list[OpportunityItem] = []
    for assessment in assessments:
        try:
            context = assemble_event_context(assessment.event_id, tables)
        except ValueError:
            context = None
        items.append(_to_item(assessment, lookup.get(assessment.event_id), context))
    if status.lower() not in {"open", "all"}:
        wanted = status.lower()
        items = [item for item in items if (item.status or "").lower() == wanted]
    runtime._opportunity_cache[cache_key] = items
    return items


def list_opportunities(
    runtime: AppRuntime,
    *,
    priority: PriorityFilter | None = None,
    status: str = "open",
    minimum_amount: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> OpportunityListResponse:
    if offset < 0 or limit < 1:
        raise APIError("INVALID_REQUEST", "limit must be >= 1 and offset must be >= 0.", status_code=400)
    items = scored_opportunities(runtime, status=status)
    if priority:
        items = [item for item in items if item.priority_category == priority]
    if minimum_amount is not None:
        items = [item for item in items if item.amount_at_risk >= minimum_amount]
    total = len(items)
    page = items[offset : offset + limit]
    return OpportunityListResponse(items=page, total=total, limit=limit, offset=offset)
