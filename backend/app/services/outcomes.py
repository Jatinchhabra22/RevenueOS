"""Aggregate persisted agent workflows into explainable recovery intelligence.

Does not train models, mutate agent_policy.json, or mix dataset ground-truth labels.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from app.schemas.api import AgentActivityItem, AgentActivityResponse, AgentWorkflowResponse
from app.schemas.entities import EventContext, Intervention
from app.schemas.outcomes import (
    AGENT_OUTCOME_DISCLAIMER,
    ActionEffectivenessResponse,
    ActionEffectivenessRow,
    LearningSignal,
    MetricBreakdownRow,
    OutcomeMetricsResponse,
    OutcomeRecord,
    SegmentIntelligenceResponse,
    SegmentRow,
)
from app.services.persistence import read_json
from app.services.runtime import AppRuntime

LOW_SAMPLE_THRESHOLD = 5
SUFFICIENT_THRESHOLD = 15
RESOLVED_OUTCOMES = {"RECOVERED", "NOT_RECOVERED"}
ATTEMPTED_OUTCOMES = {"RECOVERED", "NOT_RECOVERED", "PENDING"}


def customer_value_segment(ltv: float | None) -> str:
    if ltv is None:
        return "unknown"
    if ltv >= 100_000:
        return "high_value"
    if ltv >= 40_000:
        return "mid_value"
    return "low_value"


def sample_quality(n: int) -> str:
    if n < LOW_SAMPLE_THRESHOLD:
        return "insufficient" if n < 3 else "low_sample"
    if n < SUFFICIENT_THRESHOLD:
        return "low_sample"
    return "sufficient"


def confidence_for(n: int) -> str:
    if n < LOW_SAMPLE_THRESHOLD:
        return "low"
    if n < SUFFICIENT_THRESHOLD:
        return "medium"
    return "high"


def _safe_rate(recovered: int, resolved: int) -> float | None:
    if resolved <= 0:
        return None
    return round(recovered / resolved, 4)


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def load_workflow_payloads(workflows_dir: Path) -> dict[str, dict[str, Any]]:
    """Unique workflows keyed by workflow_id. Later writes replace earlier ones."""
    by_id: dict[str, dict[str, Any]] = {}
    if not workflows_dir.exists():
        return by_id
    for hist in workflows_dir.glob("*/history.jsonl"):
        try:
            lines = hist.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            workflow_id = _as_str(payload.get("workflow_id"))
            if workflow_id:
                by_id[workflow_id] = payload
    for latest in workflows_dir.glob("*/latest.json"):
        try:
            payload = read_json(latest)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        workflow_id = _as_str(payload.get("workflow_id"))
        if workflow_id:
            by_id[workflow_id] = payload
    return by_id


def _event_lookup(runtime: AppRuntime | None) -> dict[str, dict[str, Any]]:
    if runtime is None:
        return {}
    try:
        events = runtime.tables()["revenue_events"]
    except Exception:
        return {}
    index: dict[str, dict[str, Any]] = {}
    for row in events.to_dict("records"):
        event_id = _as_str(row.get("event_id"))
        if event_id:
            index[event_id] = row
    return index


def outcome_record_from_payload(
    payload: dict[str, Any],
    event_row: dict[str, Any] | None = None,
) -> OutcomeRecord | None:
    workflow_id = _as_str(payload.get("workflow_id"))
    event_id = _as_str(payload.get("event_id"))
    if not workflow_id or not event_id:
        return None
    risk = payload.get("risk_assessment") or {}
    selected = payload.get("selected_action") or {}
    outcome = payload.get("outcome") or {}
    execution = payload.get("execution_result") or payload.get("tool_result") or {}
    guardrail = payload.get("guardrail_result") or {}
    extra = payload.get("outcome_context") or {}
    event_row = event_row or {}

    amount_recovered = _as_float(outcome.get("amount_recovered")) if outcome else None
    ltv = _as_float(extra.get("customer_ltv"))
    if ltv is None:
        ltv = _as_float(risk.get("customer_ltv"))

    timestamp = _iso(outcome.get("timestamp")) or _iso(execution.get("timestamp"))
    failure_reason = _as_str(extra.get("failure_reason")) or _as_str(event_row.get("failure_reason"))
    payment_method = _as_str(extra.get("payment_method")) or _as_str(event_row.get("payment_method"))
    event_type = _as_str(extra.get("event_type")) or _as_str(event_row.get("event_type"))

    return OutcomeRecord(
        workflow_id=workflow_id,
        event_id=event_id,
        customer_id=_as_str(risk.get("customer_id")) or _as_str(event_row.get("customer_id")),
        action_type=_as_str(selected.get("action_type")),
        priority_category=_as_str(risk.get("priority_category")),
        priority_score=_as_float(risk.get("priority_score")),
        amount_at_risk=_as_float(risk.get("amount_at_risk")),
        recovery_probability=_as_float(risk.get("recovery_probability")),
        churn_probability=_as_float(risk.get("churn_probability")),
        expected_recovery_value=_as_float(risk.get("expected_recovery_value")),
        outcome=_as_str(outcome.get("outcome")) if outcome else None,
        amount_recovered=amount_recovered,
        execution_status=_as_str(execution.get("status")) if execution else None,
        timestamp=timestamp,
        guardrail_status=_as_str(guardrail.get("status")),
        failure_reason=failure_reason,
        payment_method=payment_method,
        event_type=event_type,
        customer_ltv=ltv,
        customer_value_segment=customer_value_segment(ltv),
        dry_run=bool(payload.get("dry_run")),
        agent_mode=_as_str(payload.get("agent_mode")),
        iterations=_as_int(payload.get("iterations")),
        provider=_as_str(payload.get("provider")),
    )


def load_outcome_records(runtime: AppRuntime) -> list[OutcomeRecord]:
    payloads = load_workflow_payloads(runtime.workflows_dir)
    events = _event_lookup(runtime)
    records: list[OutcomeRecord] = []
    for payload in payloads.values():
        event_id = _as_str(payload.get("event_id"))
        record = outcome_record_from_payload(payload, events.get(event_id or ""))
        if record is not None:
            records.append(record)
    records.sort(key=lambda item: item.timestamp or "", reverse=True)
    return records


def _recovered_amount(record: OutcomeRecord) -> float:
    if record.amount_recovered is None:
        return 0.0
    return float(record.amount_recovered)


def _breakdown(records: Iterable[OutcomeRecord], key_fn) -> list[MetricBreakdownRow]:
    groups: dict[str, list[OutcomeRecord]] = defaultdict(list)
    for record in records:
        key = key_fn(record) or "unknown"
        groups[str(key)].append(record)
    rows: list[MetricBreakdownRow] = []
    for key, group in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        recovered = sum(1 for item in group if item.outcome == "RECOVERED")
        resolved = sum(1 for item in group if item.outcome in RESOLVED_OUTCOMES)
        attempted = [item for item in group if item.outcome in ATTEMPTED_OUTCOMES]
        rows.append(
            MetricBreakdownRow(
                key=key,
                executions=len(group),
                recovered_count=recovered,
                recovery_rate=_safe_rate(recovered, resolved),
                amount_recovered=round(sum(_recovered_amount(item) for item in group), 2),
                amount_attempted=round(sum(item.amount_at_risk or 0.0 for item in attempted), 2),
                low_sample_size=len(group) < LOW_SAMPLE_THRESHOLD,
            )
        )
    return rows


def aggregate_outcomes(records: list[OutcomeRecord]) -> OutcomeMetricsResponse:
    recovered = [item for item in records if item.outcome == "RECOVERED"]
    unsuccessful = [item for item in records if item.outcome == "NOT_RECOVERED"]
    pending = [item for item in records if item.outcome == "PENDING"]
    blocked = [item for item in records if item.outcome == "BLOCKED"]
    no_action = [item for item in records if item.outcome == "NO_ACTION"]
    resolved = recovered + unsuccessful
    attempted = [item for item in records if item.outcome in ATTEMPTED_OUTCOMES]
    missing_amount = sum(
        1 for item in recovered if item.amount_recovered is None
    )
    amount_recovered = round(sum(_recovered_amount(item) for item in records), 2)
    avg_recovered = round(amount_recovered / len(recovered), 2) if recovered else None
    expected_sum = round(sum(item.expected_recovery_value or 0.0 for item in resolved), 2)
    observed_sum = round(sum(_recovered_amount(item) for item in resolved), 2)
    by_action = _breakdown(records, lambda item: item.action_type)
    top_action = None
    ranked = [
        row
        for row in by_action
        if row.recovery_rate is not None and not row.low_sample_size
    ]
    if ranked:
        ranked.sort(key=lambda row: (row.recovery_rate or 0, row.executions), reverse=True)
        top_action = ranked[0].key
    elif by_action:
        with_rate = [row for row in by_action if row.recovery_rate is not None]
        pool = with_rate or by_action
        pool.sort(key=lambda row: (row.recovery_rate or -1, row.executions), reverse=True)
        top_action = pool[0].key
        if pool[0].low_sample_size:
            top_action = f"{top_action} (low sample size)"
    return OutcomeMetricsResponse(
        disclaimer=AGENT_OUTCOME_DISCLAIMER,
        executions=len(records),
        successful_recoveries=len(recovered),
        unsuccessful_recoveries=len(unsuccessful),
        pending_outcomes=len(pending),
        blocked_actions=len(blocked),
        no_action_outcomes=len(no_action),
        recovery_rate=_safe_rate(len(recovered), len(resolved)),
        total_amount_recovered=amount_recovered,
        total_amount_attempted=round(sum(item.amount_at_risk or 0.0 for item in attempted), 2),
        average_recovered_amount=avg_recovered,
        expected_recovery_sum=expected_sum,
        observed_recovery_sum=observed_sum,
        missing_amount_recovered_count=missing_amount,
        top_performing_action=top_action,
        recovery_by_action_type=by_action,
        recovery_by_priority=_breakdown(records, lambda item: item.priority_category),
        recovery_by_failure_reason=_breakdown(records, lambda item: item.failure_reason),
        recovery_by_payment_method=_breakdown(records, lambda item: item.payment_method),
        recovery_by_event_type=_breakdown(records, lambda item: item.event_type),
    )


def action_effectiveness(
    records: list[OutcomeRecord],
    action_type: str | None = None,
) -> ActionEffectivenessResponse:
    filtered = records
    if action_type:
        filtered = [item for item in records if item.action_type == action_type]
    groups: dict[str, list[OutcomeRecord]] = defaultdict(list)
    for record in filtered:
        if record.action_type:
            groups[record.action_type].append(record)
    items: list[ActionEffectivenessRow] = []
    for name, group in sorted(groups.items()):
        recovered = [item for item in group if item.outcome == "RECOVERED"]
        resolved = [item for item in group if item.outcome in RESOLVED_OUTCOMES]
        amount = round(sum(_recovered_amount(item) for item in group), 2)
        expected = round(sum(item.expected_recovery_value or 0.0 for item in resolved), 2)
        observed = round(sum(_recovered_amount(item) for item in resolved), 2)
        probs = [item.recovery_probability for item in group if item.recovery_probability is not None]
        items.append(
            ActionEffectivenessRow(
                action_type=name,
                execution_count=len(group),
                recovered_count=len(recovered),
                recovery_rate=_safe_rate(len(recovered), len(resolved)),
                amount_recovered=amount,
                average_recovered_amount=round(amount / len(recovered), 2) if recovered else None,
                average_recovery_probability=round(sum(probs) / len(probs), 4) if probs else None,
                expected_recovery_value=expected,
                observed_recovery=observed,
                observed_vs_expected=round(observed - expected, 2) if resolved else None,
                low_sample_size=len(group) < LOW_SAMPLE_THRESHOLD,
                sample_quality=sample_quality(len(group)),  # type: ignore[arg-type]
            )
        )
    items.sort(key=lambda row: (row.recovery_rate is None, -(row.recovery_rate or 0), -row.execution_count))
    return ActionEffectivenessResponse(disclaimer=AGENT_OUTCOME_DISCLAIMER, items=items)


def learning_signals(records: list[OutcomeRecord]) -> list[LearningSignal]:
    groups: dict[tuple[str, str], list[OutcomeRecord]] = defaultdict(list)
    for record in records:
        if not record.action_type or not record.failure_reason:
            continue
        groups[(record.action_type, record.failure_reason)].append(record)
    signals: list[LearningSignal] = []
    for (action_type, segment), group in groups.items():
        recovered = sum(1 for item in group if item.outcome == "RECOVERED")
        resolved = sum(1 for item in group if item.outcome in RESOLVED_OUTCOMES)
        signals.append(
            LearningSignal(
                action_type=action_type,
                segment=segment,
                segment_dimension="failure_reason",
                observations=len(group),
                observed_recovery_rate=_safe_rate(recovered, resolved),
                confidence=confidence_for(len(group)),  # type: ignore[arg-type]
                sample_quality=sample_quality(len(group)),  # type: ignore[arg-type]
            )
        )
    signals.sort(key=lambda item: (-item.observations, item.segment, item.action_type))
    return signals


def historical_intelligence_for_context(
    records: list[OutcomeRecord],
    *,
    failure_reason: str | None,
) -> list[LearningSignal]:
    if not failure_reason:
        return []
    return [item for item in learning_signals(records) if item.segment == failure_reason]


def _segment_observations(items: list[SegmentRow]) -> list[str]:
    notes: list[str] = []
    combos = [row for row in items if row.action_type and row.dimension == "failure_reason"]
    by_segment: dict[str, list[SegmentRow]] = defaultdict(list)
    for row in combos:
        by_segment[row.segment].append(row)
    for segment, rows in sorted(by_segment.items()):
        scored = [row for row in rows if row.recovery_rate is not None]
        if len(scored) < 2:
            continue
        scored.sort(key=lambda row: (row.recovery_rate or 0, row.executions), reverse=True)
        best, second = scored[0], scored[1]
        qualifier = "In this demo dataset, "
        if best.low_sample_size or second.low_sample_size:
            qualifier += "(low sample size) "
        notes.append(
            f"{qualifier}{best.action_type} recovered more often than {second.action_type} "
            f"for {segment} failures "
            f"({best.recovery_rate:.0%} vs {second.recovery_rate:.0%}; "
            f"n={best.executions} vs {second.executions}). "
            "This is a demo observation, not a universal claim."
        )
    high_value = [
        row
        for row in items
        if row.dimension == "customer_value_segment" and row.segment == "high_value" and not row.action_type
    ]
    if high_value and high_value[0].executions:
        notes.append(
            "High-value events can carry higher expected recovery and may still need lower-friction "
            "interventions. Demo observation only — not a statistical finding."
        )
    return notes[:8]


def segment_intelligence(records: list[OutcomeRecord]) -> SegmentIntelligenceResponse:
    items: list[SegmentRow] = []
    dimensions = (
        ("failure_reason", lambda item: item.failure_reason),
        ("payment_method", lambda item: item.payment_method),
        ("event_type", lambda item: item.event_type),
        ("priority_category", lambda item: item.priority_category),
        ("customer_value_segment", lambda item: item.customer_value_segment),
    )
    for name, getter in dimensions:
        for row in _breakdown(records, getter):
            items.append(
                SegmentRow(
                    dimension=name,
                    segment=row.key,
                    action_type=None,
                    executions=row.executions,
                    recovered_count=row.recovered_count,
                    recovery_rate=row.recovery_rate,
                    amount_recovered=row.amount_recovered,
                    low_sample_size=row.low_sample_size,
                )
            )
    combos: dict[tuple[str, str], list[OutcomeRecord]] = defaultdict(list)
    for record in records:
        if record.failure_reason and record.action_type:
            combos[(record.failure_reason, record.action_type)].append(record)
    for (segment, action_type), group in sorted(combos.items()):
        recovered = sum(1 for item in group if item.outcome == "RECOVERED")
        resolved = sum(1 for item in group if item.outcome in RESOLVED_OUTCOMES)
        items.append(
            SegmentRow(
                dimension="failure_reason",
                segment=segment,
                action_type=action_type,
                executions=len(group),
                recovered_count=recovered,
                recovery_rate=_safe_rate(recovered, resolved),
                amount_recovered=round(sum(_recovered_amount(item) for item in group), 2),
                low_sample_size=len(group) < LOW_SAMPLE_THRESHOLD,
            )
        )
    return SegmentIntelligenceResponse(
        disclaimer=AGENT_OUTCOME_DISCLAIMER,
        items=items,
        observations=_segment_observations(items),
        learning_signals=learning_signals(records),
    )


def list_persisted_activity(runtime: AppRuntime) -> AgentActivityResponse:
    records = load_outcome_records(runtime)
    items = [
        AgentActivityItem(
            workflow_id=record.workflow_id,
            event_id=record.event_id,
            customer_id=record.customer_id or "",
            selected_action=record.action_type or "",
            guardrail_status=record.guardrail_status or "",
            outcome=record.outcome,
            execution_status=record.execution_status,
            timestamp=record.timestamp,
            amount_recovered=_recovered_amount(record),
            dry_run=record.dry_run,
            priority_category=record.priority_category,
            amount_at_risk=record.amount_at_risk,
            expected_recovery_value=record.expected_recovery_value,
            agent_mode=record.agent_mode,
            iterations=record.iterations,
            provider=record.provider,
        )
        for record in records
    ]
    return AgentActivityResponse(items=items, total=len(items))


def simulated_interventions_for_event(runtime: AppRuntime, event_id: str) -> list[Intervention]:
    """Treat persisted simulated executions as prior interventions for guardrails."""
    from datetime import datetime, timezone

    items: list[Intervention] = []
    for payload in load_workflow_payloads(runtime.workflows_dir).values():
        if _as_str(payload.get("event_id")) != event_id:
            continue
        history = payload.get("iteration_history") or []
        risk = payload.get("risk_assessment") or {}
        workflow_id = _as_str(payload.get("workflow_id")) or "WF"
        if history:
            for index, step in enumerate(history, start=1):
                action_type = _as_str(step.get("action_type"))
                if not action_type:
                    continue
                raw_ts = step.get("timestamp")
                try:
                    ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00")) if raw_ts else datetime.now(timezone.utc)
                except ValueError:
                    ts = datetime.now(timezone.utc)
                items.append(
                    Intervention(
                        intervention_id=f"SIM_{workflow_id}_{index}",
                        event_id=event_id,
                        customer_id=_as_str(risk.get("customer_id")) or "unknown",
                        action_type=action_type,
                        action_timestamp=ts,
                        attempt_number=index,
                        outcome=_as_str(step.get("outcome")) or "unknown",
                        amount_recovered=_as_float(step.get("amount_recovered")),
                    )
                )
            continue
        execution = payload.get("execution_result") or payload.get("tool_result") or {}
        if not execution:
            continue
        outcome = payload.get("outcome") or {}
        if _as_str(outcome.get("outcome")) in {"BLOCKED", None} and not execution:
            continue
        workflow_id = _as_str(payload.get("workflow_id")) or "WF"
        selected = payload.get("selected_action") or {}
        risk = payload.get("risk_assessment") or {}
        raw_ts = execution.get("timestamp") or outcome.get("timestamp")
        try:
            ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00")) if raw_ts else datetime.now(timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)
        items.append(
            Intervention(
                intervention_id=f"SIM_{workflow_id}",
                event_id=event_id,
                customer_id=_as_str(risk.get("customer_id")) or "unknown",
                action_type=_as_str(selected.get("action_type")) or "unknown",
                action_timestamp=ts,
                attempt_number=len(items) + 1,
                outcome=_as_str(outcome.get("outcome")) or "unknown",
                amount_recovered=_as_float(outcome.get("amount_recovered")),
            )
        )
    return items


def outcome_context_payload(context: EventContext) -> dict[str, Any]:
    event = context.event
    ltv = context.customer.customer_ltv if context.customer else None
    return {
        "failure_reason": event.failure_reason,
        "payment_method": event.payment_method,
        "event_type": event.event_type,
        "customer_ltv": ltv,
    }


def workflow_to_activity_item(workflow: AgentWorkflowResponse) -> AgentActivityItem:
    timestamp = None
    if workflow.outcome:
        timestamp = _iso(workflow.outcome.timestamp)
    elif workflow.execution_result:
        timestamp = _iso(workflow.execution_result.timestamp)
    return AgentActivityItem(
        workflow_id=workflow.workflow_id,
        event_id=workflow.event_id,
        customer_id=workflow.risk_assessment.customer_id,
        selected_action=workflow.selected_action.action_type,
        guardrail_status=workflow.guardrail_result.status,
        outcome=workflow.outcome.outcome if workflow.outcome else None,
        execution_status=workflow.execution_result.status if workflow.execution_result else None,
        timestamp=timestamp,
        amount_recovered=workflow.outcome.amount_recovered if workflow.outcome else 0.0,
        dry_run=workflow.dry_run,
        priority_category=workflow.risk_assessment.priority_category,
        amount_at_risk=workflow.risk_assessment.amount_at_risk,
        expected_recovery_value=workflow.risk_assessment.expected_recovery_value,
    )
