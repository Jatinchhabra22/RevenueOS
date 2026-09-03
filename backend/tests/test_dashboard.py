from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_runtime
from app.core.config import get_settings
from app.main import app
from app.schemas.api import MetricsDashboardResponse, MetricsOverviewResponse
from app.schemas.outcomes import OutcomeRecord
from app.services.dashboard import dashboard_metrics
from app.services.data.synthetic import GeneratorConfig, generate_tables
from app.services.outcomes import action_effectiveness, aggregate_outcomes
from app.services.runtime import AppRuntime


def _write_csv(directory: Path, tables: dict[str, pd.DataFrame]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


@pytest.fixture
def runtime(tmp_path: Path) -> AppRuntime:
    tables = generate_tables(GeneratorConfig(seed=11, n_customers=40))
    active = tmp_path / "data" / "demo"
    _write_csv(active, tables)
    settings = get_settings()
    return AppRuntime(
        data_dir=tmp_path / "data",
        artifacts_dir=settings.artifacts_path,
        models_dir=settings.models_path,
        uploads_dir=tmp_path / "data" / "uploads",
        workflows_dir=tmp_path / "artifacts" / "workflows",
        active_dataset_dir=active,
        upload_max_bytes=2_000_000,
        disable_llm=True,
    )


@pytest.fixture
def api_client(runtime: AppRuntime) -> TestClient:
    app.dependency_overrides[get_runtime] = lambda: runtime
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


def _record(**overrides) -> OutcomeRecord:
    payload = dict(
        workflow_id="WF_1",
        event_id="EVT_1",
        action_type="retry_later",
        priority_category="HIGH",
        amount_at_risk=1000.0,
        expected_recovery_value=400.0,
        outcome="RECOVERED",
        amount_recovered=1000.0,
        timestamp="2026-09-01T10:00:00+00:00",
        failure_reason="insufficient_funds",
    )
    payload.update(overrides)
    return OutcomeRecord.model_validate(payload)


def test_existing_overview_contract_unchanged(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/metrics/overview")
    assert response.status_code == 200
    MetricsOverviewResponse.model_validate(response.json())
    body = response.json()
    assert "opportunities" in body
    assert "agent_executions" in body
    assert "funnel" not in body


def test_dashboard_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/metrics/dashboard")
    assert response.status_code == 200
    payload = MetricsDashboardResponse.model_validate(response.json())
    assert payload.funnel.revenue_at_risk >= 0
    assert payload.funnel.predicted_recoverable_value >= 0
    assert payload.funnel.predicted_recoverable_value <= payload.funnel.revenue_at_risk + 1e-6
    assert {row.key for row in payload.recoverability} >= {
        "RECOVERABLE",
        "LOW_RECOVERABILITY",
        "NOT_RECOVERABLE",
        "ALREADY_RESOLVED",
        "ACTION_BLOCKED",
        "NEEDS_REVIEW",
    }
    assert {row.key for row in payload.risk_by_level} == {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert payload.funnel.revenue_targeted_available is False
    assert payload.activity_trend_available is False


def test_dashboard_zero_and_missing_outcomes(runtime: AppRuntime) -> None:
    payload = dashboard_metrics(runtime)
    assert payload.funnel.actual_recovered is None
    assert payload.kpis["blocked_actions"] == 0
    assert payload.kpis["workflow_count"] == 0
    empty = aggregate_outcomes([])
    assert empty.recovery_rate is None
    assert empty.total_amount_recovered == 0


def test_failure_reason_and_risk_aggregation(runtime: AppRuntime) -> None:
    payload = dashboard_metrics(runtime)
    assert payload.failure_reasons
    assert all(row.amount >= 0 for row in payload.failure_reasons)
    assert sum(row.count for row in payload.risk_by_level) == payload.kpis["high_critical_events"] + sum(
        row.count for row in payload.risk_by_level if row.key in {"MEDIUM", "LOW"}
    )


def test_predicted_vs_actual_not_equal_to_at_risk() -> None:
    records = [
        _record(workflow_id="A", expected_recovery_value=400, amount_recovered=0, outcome="NOT_RECOVERED"),
        _record(workflow_id="B", expected_recovery_value=400, amount_recovered=400, outcome="RECOVERED"),
    ]
    metrics = aggregate_outcomes(records)
    assert metrics.expected_recovery_sum == 800
    assert metrics.observed_recovery_sum == 400
    assert metrics.expected_recovery_sum != sum(item.amount_at_risk or 0 for item in records)


def test_small_sample_size_label() -> None:
    records = [_record(workflow_id=f"WF_{index}", amount_recovered=1000, outcome="RECOVERED") for index in range(3)]
    items = action_effectiveness(records).items
    assert items[0].recovery_rate == 1.0
    assert items[0].execution_count == 3
    assert items[0].low_sample_size is True
    assert items[0].sample_quality in {"insufficient", "low_sample"}
    from app.services.dashboard import _confidence_label

    assert "Low confidence" in _confidence_label(3, items[0].sample_quality) or "Insufficient" in _confidence_label(
        3, items[0].sample_quality
    )
