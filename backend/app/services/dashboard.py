"""Read-only overview aggregations. Predicted ERV stays separate from observed recovery."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import pandas as pd

from app.schemas.api import (
    ActionPerformanceRow,
    ActivityTrendPoint,
    MetricsDashboardResponse,
    NamedCountAmount,
    PredictedVsActualRow,
    RecoveryFunnel,
    TopOpportunityChartRow,
)
from app.schemas.outcomes import AGENT_OUTCOME_DISCLAIMER
from app.services.dataset import build_summary
from app.services.opportunities import scored_opportunities
from app.services.outcomes import action_effectiveness, aggregate_outcomes, load_outcome_records
from app.services.runtime import AppRuntime

_RECOVERABILITY_ORDER = [
    "RECOVERABLE",
    "LOW_RECOVERABILITY",
    "NOT_RECOVERABLE",
    "ALREADY_RESOLVED",
    "ACTION_BLOCKED",
    "NEEDS_REVIEW",
]
_OUTCOME_ORDER = [
    "RECOVERED",
    "NOT_RECOVERED",
    "PENDING",
    "NO_ACTION",
    "BLOCKED",
    "ESCALATED",
]


def _confidence_label(executions: int, quality: str) -> str:
    if executions <= 0 or executions < 3 or quality == "insufficient":
        return "Insufficient observations"
    if executions < 5 or quality == "low_sample":
        return "Low confidence · Limited sample"
    return "Observational result"


def _resolved_bucket(runtime: AppRuntime) -> NamedCountAmount:
    events = runtime.tables().get("revenue_events", pd.DataFrame())
    if events.empty or "event_status" not in events.columns:
        return NamedCountAmount(key="ALREADY_RESOLVED", count=0, amount=0.0)
    mask = events["event_status"].astype(str).str.lower().isin(
        {"recovered", "closed", "resolved", "cancelled", "paid", "completed"}
    )
    rows = events[mask]
    amount = 0.0
    if "amount_at_risk" in rows.columns and not rows.empty:
        amount = float(pd.to_numeric(rows["amount_at_risk"], errors="coerce").fillna(0).sum())
    return NamedCountAmount(key="ALREADY_RESOLVED", count=int(len(rows)), amount=round(amount, 2))


def dashboard_metrics(runtime: AppRuntime) -> MetricsDashboardResponse:
    open_items = scored_opportunities(runtime, status="open")
    records = load_outcome_records(runtime)
    outcomes = aggregate_outcomes(records)
    actions = action_effectiveness(records)
    summary = build_summary(runtime)
    resolved = _resolved_bucket(runtime)

    revenue_at_risk = round(sum(item.amount_at_risk for item in open_items), 2)
    predicted = round(sum(item.expected_recovery_value for item in open_items), 2)
    has_workflows = len(records) > 0
    targeted = None
    if has_workflows:
        targeted = round(
            sum(
                item.amount_at_risk or 0.0
                for item in records
                if item.action_type not in {None, "stop_recovery"}
                and item.outcome not in {"NO_ACTION", "BLOCKED"}
            ),
            2,
        )
    actual = outcomes.total_amount_recovered if has_workflows else None

    recoverability_map: dict[str, list] = defaultdict(list)
    for item in open_items:
        recoverability_map[item.recoverability or "NEEDS_REVIEW"].append(item)
    recoverability_rows = []
    for key in _RECOVERABILITY_ORDER:
        if key == "ALREADY_RESOLVED":
            recoverability_rows.append(resolved)
            continue
        group = recoverability_map.get(key, [])
        recoverability_rows.append(
            NamedCountAmount(
                key=key,
                count=len(group),
                amount=round(sum(row.amount_at_risk for row in group), 2),
                expected_recoverable_value=round(sum(row.expected_recovery_value for row in group), 2),
            )
        )

    risk_rows = [
        NamedCountAmount(
            key=category,
            count=sum(1 for item in open_items if item.priority_category == category),
            amount=round(sum(item.amount_at_risk for item in open_items if item.priority_category == category), 2),
            expected_recoverable_value=round(
                sum(item.expected_recovery_value for item in open_items if item.priority_category == category),
                2,
            ),
        )
        for category in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    ]

    failure_map: dict[str, list] = defaultdict(list)
    for item in open_items:
        failure_map[item.failure_reason or "unknown"].append(item)
    failure_rows = [
        NamedCountAmount(
            key=key,
            count=len(group),
            amount=round(sum(row.amount_at_risk for row in group), 2),
            expected_recoverable_value=round(sum(row.expected_recovery_value for row in group), 2),
        )
        for key, group in failure_map.items()
    ]
    failure_rows.sort(key=lambda row: row.amount, reverse=True)

    outcome_counts = {
        "RECOVERED": outcomes.successful_recoveries,
        "NOT_RECOVERED": outcomes.unsuccessful_recoveries,
        "PENDING": outcomes.pending_outcomes,
        "NO_ACTION": outcomes.no_action_outcomes,
        "BLOCKED": outcomes.blocked_actions,
        "ESCALATED": sum(1 for item in records if item.outcome == "ESCALATED"),
    }
    outcome_rows = [NamedCountAmount(key=key, count=outcome_counts[key]) for key in _OUTCOME_ORDER]

    predicted_groups: dict[str, list] = defaultdict(list)
    for item in records:
        predicted_groups[item.priority_category or "unknown"].append(item)
    predicted_vs_actual = [
        PredictedVsActualRow(
            key=key,
            predicted_recoverable_value=round(sum(item.expected_recovery_value or 0.0 for item in group), 2),
            actual_recovered=round(sum(item.amount_recovered or 0.0 for item in group), 2),
            executions=len(group),
        )
        for key, group in predicted_groups.items()
    ]
    predicted_vs_actual.sort(key=lambda row: row.predicted_recoverable_value, reverse=True)

    action_rows = [
        ActionPerformanceRow(
            action_type=row.action_type,
            observed_recovery_rate=row.recovery_rate,
            execution_count=row.execution_count,
            amount_recovered=row.amount_recovered,
            recovered_count=row.recovered_count,
            low_sample_size=row.low_sample_size,
            sample_quality=row.sample_quality,
            confidence_label=_confidence_label(row.execution_count, row.sample_quality),
        )
        for row in actions.items
    ]

    by_date: dict[str, list] = defaultdict(list)
    for item in records:
        if not item.timestamp:
            continue
        try:
            parsed = datetime.fromisoformat(item.timestamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        by_date[parsed.date().isoformat()].append(item)
    trend_points = [
        ActivityTrendPoint(
            date=day,
            recovery_attempts=sum(1 for item in group if item.action_type not in {None, "stop_recovery"}),
            successful_recoveries=sum(1 for item in group if item.outcome == "RECOVERED"),
            amount_recovered=round(sum(item.amount_recovered or 0.0 for item in group), 2),
        )
        for day, group in sorted(by_date.items())
    ]
    trend_available = len(trend_points) >= 2

    top_rows = [
        TopOpportunityChartRow(
            event_id=item.event_id,
            customer_id=item.customer_id,
            amount_at_risk=item.amount_at_risk,
            expected_recovery_value=item.expected_recovery_value,
            priority_score=item.priority_score,
            priority_category=item.priority_category,
            recoverability=item.recoverability,
            failure_reason=item.failure_reason,
        )
        for item in open_items[:8]
    ]

    no_action_open = sum(1 for item in open_items if item.pursue is False)
    coverage = (
        round(sum(1 for item in open_items if item.recoverability == "RECOVERABLE") / len(open_items), 4)
        if open_items
        else None
    )
    return MetricsDashboardResponse(
        funnel=RecoveryFunnel(
            revenue_at_risk=revenue_at_risk,
            predicted_recoverable_value=predicted,
            revenue_targeted=targeted,
            actual_recovered=actual,
            revenue_targeted_available=has_workflows,
            actual_recovered_available=has_workflows,
        ),
        risk_by_level=risk_rows,
        recoverability=recoverability_rows,
        outcomes=outcome_rows,
        failure_reasons=failure_rows[:12],
        predicted_vs_actual=predicted_vs_actual,
        predicted_vs_actual_grouping="priority",
        actions=action_rows,
        activity_trend=trend_points if trend_available else [],
        activity_trend_available=trend_available,
        activity_trend_reason=None if trend_available else "Insufficient time-series data in persisted workflows.",
        top_opportunities=top_rows,
        kpis={
            "revenue_at_risk": revenue_at_risk,
            "expected_recoverable_value": predicted,
            "actual_recovered": actual if actual is not None else 0.0,
            "observed_event_recovery_rate": outcomes.recovery_rate,
            "recoverability_coverage": coverage,
            "high_critical_events": sum(1 for item in open_items if item.priority_category in {"HIGH", "CRITICAL"}),
            "no_action_open_events": no_action_open,
            "blocked_actions": outcomes.blocked_actions,
            "dataset_recovered_events": summary.recovered_event_count,
            "workflow_count": outcomes.executions,
        },
        disclaimer=AGENT_OUTCOME_DISCLAIMER,
    )
