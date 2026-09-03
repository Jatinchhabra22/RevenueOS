"""Aggregate dashboard metrics. Dataset/model numbers stay separate from agent runs."""

from __future__ import annotations

from app.schemas.api import (
    AgentExecutionMetrics,
    DatasetMetrics,
    MetricsOverviewResponse,
    OpportunityMetrics,
)
from app.services.dataset import build_summary
from app.services.opportunities import scored_opportunities
from app.services.outcomes import aggregate_outcomes, load_outcome_records
from app.services.runtime import AppRuntime


def _agent_metrics(runtime: AppRuntime) -> AgentExecutionMetrics:
    summary = aggregate_outcomes(load_outcome_records(runtime))
    return AgentExecutionMetrics(
        workflow_count=summary.executions,
        recovered_outcomes=summary.successful_recoveries,
        not_recovered_outcomes=summary.unsuccessful_recoveries,
        pending_outcomes=summary.pending_outcomes,
        blocked_outcomes=summary.blocked_actions,
        no_action_outcomes=summary.no_action_outcomes,
        simulated_amount_recovered=summary.total_amount_recovered,
    )


def overview_metrics(runtime: AppRuntime) -> MetricsOverviewResponse:
    summary = build_summary(runtime)
    items = scored_opportunities(runtime, status="open")
    n = len(items)
    avg_recovery = round(sum(item.recovery_probability for item in items) / n, 4) if n else None
    avg_churn = round(sum(item.churn_probability for item in items) / n, 4) if n else None
    breakdown = []
    for category in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        rows = [item for item in items if item.priority_category == category]
        breakdown.append(
            {
                "priority_category": category,
                "count": len(rows),
                "revenue_at_risk": round(sum(item.amount_at_risk for item in rows), 2),
                "expected_recoverable_revenue": round(sum(item.expected_recovery_value for item in rows), 2),
            }
        )
    return MetricsOverviewResponse(
        dataset=DatasetMetrics(
            open_event_count=summary.open_event_count,
            recovered_event_count=summary.recovered_event_count,
            revenue_event_count=summary.revenue_event_count,
        ),
        opportunities=OpportunityMetrics(
            open_opportunities=n,
            revenue_at_risk=round(sum(item.amount_at_risk for item in items), 2),
            expected_recoverable_revenue=round(sum(item.expected_recovery_value for item in items), 2),
            critical_count=sum(1 for item in items if item.priority_category == "CRITICAL"),
            high_count=sum(1 for item in items if item.priority_category == "HIGH"),
            medium_count=sum(1 for item in items if item.priority_category == "MEDIUM"),
            low_count=sum(1 for item in items if item.priority_category == "LOW"),
            average_recovery_probability=avg_recovery,
            average_churn_probability=avg_churn,
            priority_breakdown=breakdown,
        ),
        agent_executions=_agent_metrics(runtime),
    )
