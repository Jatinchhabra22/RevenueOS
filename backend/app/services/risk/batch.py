"""Score a dataset of events with existing prediction services + risk engine."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

from app.services.data.context import assemble_event_context
from app.services.prediction.inference import predict_churn, predict_recovery
from app.services.risk.engine import assess_revenue_risk, rank_opportunities
from app.schemas.risk import RiskAssessment

EventFilter = Literal["open", "all"]


def score_events(
    tables: dict,
    *,
    status_filter: EventFilter = "open",
    artifacts_dir: Path | None = None,
    limit: int | None = None,
) -> list[RiskAssessment]:
    events = tables["revenue_events"]
    if status_filter == "open" and "event_status" in events.columns:
        events = events[events["event_status"].astype(str).str.lower() == "open"]
    event_ids = [str(value) for value in events["event_id"].tolist()]
    if limit is not None:
        event_ids = event_ids[:limit]

    assessments: list[RiskAssessment] = []
    for event_id in event_ids:
        context = assemble_event_context(event_id, tables)
        recovery = predict_recovery(context, artifacts_dir)
        churn = predict_churn(context, artifacts_dir)
        assessments.append(assess_revenue_risk(context, recovery, churn))
    return rank_opportunities(assessments)


def summarize_assessments(assessments: list[RiskAssessment]) -> dict[str, Any]:
    counts = Counter(item.priority_category for item in assessments)
    return {
        "n_events": len(assessments),
        "total_revenue_at_risk": round(sum(item.amount_at_risk for item in assessments), 2),
        "total_expected_recoverable_revenue": round(
            sum(item.expected_recovery_value for item in assessments), 2
        ),
        "priority_counts": {
            "CRITICAL": int(counts.get("CRITICAL", 0)),
            "HIGH": int(counts.get("HIGH", 0)),
            "MEDIUM": int(counts.get("MEDIUM", 0)),
            "LOW": int(counts.get("LOW", 0)),
        },
        "top_opportunities": [
            {
                "event_id": item.event_id,
                "customer_id": item.customer_id,
                "priority_category": item.priority_category,
                "priority_score": item.priority_score,
                "amount_at_risk": item.amount_at_risk,
                "expected_recovery_value": item.expected_recovery_value,
                "recovery_probability": item.recovery_probability,
                "churn_probability": item.churn_probability,
                "contributing_factors": item.contributing_factors,
            }
            for item in assessments[:10]
        ],
    }
