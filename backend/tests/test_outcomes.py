from __future__ import annotations

from pathlib import Path

from app.agents.candidates import generate_candidate_actions
from app.agents.graph import run_recovery_agent
from app.agents.llm.fallback import fallback_select_action
from app.core.config import get_settings
from app.schemas.outcomes import LearningSignal, OutcomeRecord
from app.services.outcomes import (
    action_effectiveness,
    aggregate_outcomes,
    learning_signals,
    load_outcome_records,
    segment_intelligence,
)
from app.services.persistence import append_jsonl, write_json_atomic
from app.services.runtime import AppRuntime
from tests.helpers import make_context, make_predictions


def _record(**overrides) -> OutcomeRecord:
    base = dict(
        workflow_id="WF_1",
        event_id="EVT_1",
        customer_id="CUS_1",
        action_type="payment_method_update",
        priority_category="HIGH",
        priority_score=60.0,
        amount_at_risk=4000.0,
        recovery_probability=0.57,
        churn_probability=0.2,
        expected_recovery_value=2280.0,
        outcome="RECOVERED",
        amount_recovered=4000.0,
        execution_status="simulated_success",
        timestamp="2026-09-01T10:00:00+00:00",
        guardrail_status="ALLOW",
        failure_reason="card_expired",
        payment_method="card",
        event_type="payment_failed",
        customer_ltv=80_000.0,
        customer_value_segment="mid_value",
    )
    base.update(overrides)
    return OutcomeRecord.model_validate(base)


def test_empty_outcome_store() -> None:
    metrics = aggregate_outcomes([])
    assert metrics.executions == 0
    assert metrics.successful_recoveries == 0
    assert metrics.recovery_rate is None
    assert metrics.total_amount_recovered == 0
    assert metrics.average_recovered_amount is None
    assert action_effectiveness([]).items == []
    assert learning_signals([]) == []


def test_single_outcome() -> None:
    metrics = aggregate_outcomes([_record()])
    assert metrics.executions == 1
    assert metrics.successful_recoveries == 1
    assert metrics.recovery_rate == 1.0
    assert metrics.total_amount_recovered == 4000.0


def test_multiple_outcomes_and_recovery_rate() -> None:
    records = [
        _record(workflow_id="A", outcome="RECOVERED", amount_recovered=1000),
        _record(workflow_id="B", outcome="NOT_RECOVERED", amount_recovered=0),
        _record(workflow_id="C", outcome="RECOVERED", amount_recovered=2000),
    ]
    metrics = aggregate_outcomes(records)
    assert metrics.executions == 3
    assert metrics.successful_recoveries == 2
    assert metrics.unsuccessful_recoveries == 1
    assert metrics.recovery_rate == 0.6667
    assert metrics.total_amount_recovered == 3000.0


def test_duplicate_workflow_ids_are_unique(tmp_path: Path) -> None:
    settings = get_settings()
    runtime = AppRuntime(
        data_dir=tmp_path / "data",
        artifacts_dir=settings.artifacts_path,
        models_dir=settings.models_path,
        uploads_dir=tmp_path / "uploads",
        workflows_dir=tmp_path / "workflows",
        active_dataset_dir=tmp_path / "missing",
        upload_max_bytes=1_000,
        disable_llm=True,
    )
    payload = {
        "workflow_id": "WF_DUP",
        "event_id": "EVT_DUP",
        "selected_action": {"action_type": "retry_now", "action_id": "a", "expected_effect": "", "rationale": ""},
        "risk_assessment": {
            "event_id": "EVT_DUP",
            "customer_id": "CUS",
            "amount_at_risk": 100,
            "recovery_probability": 0.5,
            "churn_probability": 0.1,
            "expected_recovery_value": 50,
            "priority_score": 10,
            "priority_category": "LOW",
            "contributing_factors": [],
        },
        "guardrail_result": {"status": "ALLOW", "allowed": True, "reason": "ok", "violations": []},
        "outcome": {"outcome": "NOT_RECOVERED", "amount_recovered": 0, "action_type": "retry_now", "execution_status": "ok", "remaining_amount_at_risk": 100, "customer_impact": "", "timestamp": "2026-01-01T00:00:00", "explanation": ""},
        "diagnosis": {},
        "recovery_prediction": {},
        "churn_prediction": {},
        "candidate_actions": [],
        "decision": {},
        "status": "completed",
        "final_decision": "completed",
    }
    later = dict(payload)
    later["outcome"] = {**payload["outcome"], "outcome": "RECOVERED", "amount_recovered": 100}
    event_dir = runtime.workflows_dir / "EVT_DUP"
    append_jsonl(event_dir / "history.jsonl", payload)
    append_jsonl(event_dir / "history.jsonl", later)
    write_json_atomic(event_dir / "latest.json", later)
    records = load_outcome_records(runtime)
    assert len(records) == 1
    assert records[0].outcome == "RECOVERED"
    assert aggregate_outcomes(records).executions == 1


def test_amount_recovered_aggregation_and_missing() -> None:
    records = [
        _record(workflow_id="A", amount_recovered=10),
        _record(workflow_id="B", amount_recovered=None, outcome="RECOVERED"),
    ]
    metrics = aggregate_outcomes(records)
    assert metrics.total_amount_recovered == 10.0
    assert metrics.missing_amount_recovered_count == 1


def test_blocked_and_pending_excluded_from_recovery_rate() -> None:
    records = [
        _record(workflow_id="A", outcome="RECOVERED"),
        _record(workflow_id="B", outcome="BLOCKED", amount_recovered=0, guardrail_status="BLOCK"),
        _record(workflow_id="C", outcome="PENDING", amount_recovered=0),
        _record(workflow_id="D", outcome="NO_ACTION", amount_recovered=0),
    ]
    metrics = aggregate_outcomes(records)
    assert metrics.blocked_actions == 1
    assert metrics.pending_outcomes == 1
    assert metrics.no_action_outcomes == 1
    assert metrics.recovery_rate == 1.0
    assert metrics.executions == 4


def test_action_effectiveness_and_low_sample() -> None:
    records = [_record(workflow_id=f"WF_{i}") for i in range(3)]
    items = action_effectiveness(records).items
    assert len(items) == 1
    assert items[0].low_sample_size is True
    assert items[0].sample_quality in {"insufficient", "low_sample"}
    filtered = action_effectiveness(records, action_type="retry_now")
    assert filtered.items == []


def test_expected_vs_observed() -> None:
    records = [
        _record(workflow_id="A", expected_recovery_value=100, amount_recovered=80, outcome="RECOVERED"),
        _record(workflow_id="B", expected_recovery_value=50, amount_recovered=0, outcome="NOT_RECOVERED"),
    ]
    metrics = aggregate_outcomes(records)
    assert metrics.expected_recovery_sum == 150
    assert metrics.observed_recovery_sum == 80
    row = action_effectiveness(records).items[0]
    assert row.expected_recovery_value == 150
    assert row.observed_recovery == 80
    assert row.observed_vs_expected == -70


def test_segment_aggregation_and_signals() -> None:
    records = [
        _record(workflow_id="A", failure_reason="card_expired", action_type="payment_method_update"),
        _record(workflow_id="B", failure_reason="card_expired", action_type="generate_payment_link", outcome="NOT_RECOVERED", amount_recovered=0),
        _record(workflow_id="C", failure_reason="insufficient_funds", action_type="retry_later", outcome="NOT_RECOVERED", amount_recovered=0),
    ]
    segments = segment_intelligence(records)
    assert any(row.dimension == "failure_reason" and row.segment == "card_expired" for row in segments.items)
    signals = learning_signals(records)
    assert any(item.action_type == "payment_method_update" and item.segment == "card_expired" for item in signals)
    assert all(item.confidence in {"low", "medium", "high"} for item in signals)


def test_historical_context_changes_fallback_among_candidates() -> None:
    context = make_context(failure_reason="card_expired")
    rec, ch = make_predictions(0.4, 0.2)
    candidates = generate_candidate_actions(context, churn=ch)
    without = fallback_select_action(candidates, context, rec, ch, None)
    assert without.selected_action_type == "payment_method_update"
    assert without.informed_by_observations is None
    historical = [
        LearningSignal(
            action_type="generate_payment_link",
            segment="card_expired",
            observations=25,
            observed_recovery_rate=0.8,
            confidence="high",
            sample_quality="sufficient",
        ),
        LearningSignal(
            action_type="payment_method_update",
            segment="card_expired",
            observations=25,
            observed_recovery_rate=0.4,
            confidence="high",
            sample_quality="sufficient",
        ),
    ]
    with_hist = fallback_select_action(candidates, context, rec, ch, None, historical=historical)
    assert with_hist.selected_action_id in {item.action_id for item in candidates}
    assert with_hist.selected_action_type == "generate_payment_link"
    assert with_hist.informed_by_observations == 25


def test_historical_intelligence_cannot_bypass_eligibility() -> None:
    context = make_context(failure_reason="card_expired")
    rec, ch = make_predictions(0.4, 0.2)
    candidates = generate_candidate_actions(context, churn=ch)
    historical = [
        LearningSignal(
            action_type="retry_now",
            segment="card_expired",
            observations=40,
            observed_recovery_rate=0.99,
            confidence="high",
            sample_quality="sufficient",
        )
    ]
    decision = fallback_select_action(candidates, context, rec, ch, None, historical=historical)
    assert decision.selected_action_type != "retry_now"
    assert "retry_now" not in {item.action_type for item in candidates}


def test_agent_graph_without_and_with_historical_intelligence() -> None:
    context = make_context(failure_reason="card_expired")
    rec, ch = make_predictions(0.4, 0.2)
    none = run_recovery_agent(
        context=context,
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert (none.get("iteration_history") or [{}])[0].get("action_type", none["selected_action"]["action_type"]) == "payment_method_update"
    historical = [
        {
            "action_type": "generate_payment_link",
            "segment": "card_expired",
            "segment_dimension": "failure_reason",
            "observations": 18,
            "observed_recovery_rate": 0.72,
            "confidence": "medium",
            "sample_quality": "sufficient",
        },
        {
            "action_type": "payment_method_update",
            "segment": "card_expired",
            "segment_dimension": "failure_reason",
            "observations": 18,
            "observed_recovery_rate": 0.3,
            "confidence": "medium",
            "sample_quality": "sufficient",
        },
    ]
    informed = run_recovery_agent(
        context=context,
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
        historical_intelligence=historical,
    )
    first_informed = (informed.get("iteration_history") or [{}])[0].get(
        "action_type",
        informed["selected_action"]["action_type"],
    )
    assert first_informed == "generate_payment_link"


def test_historical_cannot_select_ineligible_retry_in_graph() -> None:
    context = make_context(failure_reason="card_expired")
    rec, ch = make_predictions(0.4, 0.2)
    result = run_recovery_agent(
        context=context,
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
        historical_intelligence=[
            {
                "action_type": "retry_now",
                "segment": "card_expired",
                "observations": 50,
                "observed_recovery_rate": 1.0,
                "confidence": "high",
                "sample_quality": "sufficient",
                "segment_dimension": "failure_reason",
            }
        ],
    )
    assert result["selected_action"]["action_type"] != "retry_now"
    assert result["selected_action"]["action_id"] in {
        item["action_id"] for item in result["candidate_actions"]
    }
