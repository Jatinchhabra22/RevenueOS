from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_runtime
from app.core.config import get_settings
from app.main import app
from app.schemas.api import (
    AgentWorkflowResponse,
    DatasetSummary,
    EventDetailResponse,
    MetricsOverviewResponse,
    OpportunityListResponse,
)
from app.services.data.synthetic import GeneratorConfig, generate_tables
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


@pytest.fixture
def tables(runtime: AppRuntime) -> dict[str, pd.DataFrame]:
    return runtime.tables()


def _open_event_id(tables: dict[str, pd.DataFrame]) -> str:
    events = tables["revenue_events"]
    open_events = events[events["event_status"].astype(str).str.lower() == "open"]
    source = open_events if not open_events.empty else events
    return str(source.iloc[0]["event_id"])


def test_legacy_and_v1_health(api_client: TestClient) -> None:
    for path in ("/health", "/api/v1/health"):
        response = api_client.get(path)
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "revenue-recovery-orchestrator",
        }


def test_dataset_summary(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    response = api_client.get("/api/v1/data/summary")
    assert response.status_code == 200
    payload = DatasetSummary.model_validate(response.json())
    assert payload.customer_count == len(tables["customers"])
    assert payload.revenue_event_count == len(tables["revenue_events"])
    assert payload.validation_status == "ok"
    assert payload.source == "demo"


def test_opportunities_pagination(api_client: TestClient) -> None:
    first = api_client.get("/api/v1/opportunities", params={"limit": 2, "offset": 0})
    second = api_client.get("/api/v1/opportunities", params={"limit": 2, "offset": 2})
    assert first.status_code == 200
    assert second.status_code == 200
    page1 = OpportunityListResponse.model_validate(first.json())
    page2 = OpportunityListResponse.model_validate(second.json())
    assert page1.limit == 2
    assert page1.offset == 0
    assert page1.total >= len(page1.items)
    if page1.items and page2.items:
        assert page1.items[0].event_id != page2.items[0].event_id
    scores = [item.priority_score for item in page1.items]
    assert scores == sorted(scores, reverse=True)


def test_opportunities_priority_filter(api_client: TestClient) -> None:
    listed = OpportunityListResponse.model_validate(api_client.get("/api/v1/opportunities", params={"limit": 50}).json())
    if not listed.items:
        pytest.skip("no open opportunities in fixture")
    category = listed.items[0].priority_category
    filtered = OpportunityListResponse.model_validate(
        api_client.get("/api/v1/opportunities", params={"priority": category, "limit": 50}).json()
    )
    assert filtered.items
    assert all(item.priority_category == category for item in filtered.items)


def test_event_detail(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    event_id = _open_event_id(tables)
    response = api_client.get(f"/api/v1/events/{event_id}")
    assert response.status_code == 200
    payload = EventDetailResponse.model_validate(response.json())
    assert payload.event.event_id == event_id
    assert payload.risk_assessment.event_id == event_id
    assert 0 <= payload.recovery_prediction.probability <= 1


def test_event_not_found(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/events/EVT_DOES_NOT_EXIST")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "EVENT_NOT_FOUND"
    assert "EVT_DOES_NOT_EXIST" in body["error"]["message"]


def test_workflow_not_found(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    event_id = _open_event_id(tables)
    response = api_client.get(f"/api/v1/events/{event_id}/agent/latest")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "WORKFLOW_NOT_FOUND"


def test_agent_run_happy_path_and_latest(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    event_id = _open_event_id(tables)
    response = api_client.post(f"/api/v1/events/{event_id}/agent/run", json={"force_recompute": True})
    assert response.status_code == 200, response.text
    payload = AgentWorkflowResponse.model_validate(response.json())
    assert payload.event_id == event_id
    assert payload.workflow_id
    assert payload.candidate_actions
    assert payload.selected_action.action_id in {item.action_id for item in payload.candidate_actions}
    assert payload.used_llm is False
    assert payload.audit_trail
    assert "next_step" not in response.json()

    latest = api_client.get(f"/api/v1/events/{event_id}/agent/latest")
    assert latest.status_code == 200
    assert latest.json()["workflow_id"] == payload.workflow_id


def test_agent_run_deterministic_fallback(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    event_id = _open_event_id(tables)
    payload = api_client.post(f"/api/v1/events/{event_id}/agent/run", json={}).json()
    assert payload["used_llm"] is False
    assert payload["decision"]["source"] == "fallback"
    assert payload["diagnosis"]["source"] == "fallback"


def test_metrics_overview(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    event_id = _open_event_id(tables)
    api_client.post(f"/api/v1/events/{event_id}/agent/run", json={})
    response = api_client.get("/api/v1/metrics/overview")
    assert response.status_code == 200
    payload = MetricsOverviewResponse.model_validate(response.json())
    assert payload.dataset.revenue_event_count == len(tables["revenue_events"])
    assert payload.opportunities.open_opportunities >= 0
    assert payload.agent_executions.workflow_count >= 1
    assert "recovered_event_count" in response.json()["dataset"]
    assert "simulated_amount_recovered" in response.json()["agent_executions"]


def test_valid_csv_upload(api_client: TestClient, runtime: AppRuntime) -> None:
    tables = generate_tables(GeneratorConfig(seed=21, n_customers=25))
    files = []
    for name, frame in tables.items():
        files.append(("files", (f"{name}.csv", frame.to_csv(index=False).encode("utf-8"), "text/csv")))
    response = api_client.post("/api/v1/data/upload", files=files)
    assert response.status_code == 200, response.text
    payload = DatasetSummary.model_validate(response.json())
    assert payload.source.startswith("upload:")
    assert payload.customer_count == 25
    assert payload.validation_status == "ok"
    assert runtime.active_dataset_dir.parent.name == "uploads"


def test_upload_ignores_sidecar_json(api_client: TestClient) -> None:
    tables = generate_tables(GeneratorConfig(seed=31, n_customers=20))
    files = [("files", ("metadata.json", b'{"ok": true}', "application/json"))]
    for name, frame in tables.items():
        files.append(("files", (f"{name}.csv", frame.to_csv(index=False).encode("utf-8"), "text/csv")))
    response = api_client.post("/api/v1/data/upload", files=files)
    assert response.status_code == 200, response.text
    assert response.json()["customer_count"] == 20


def test_upload_accepts_zip_of_csv_folder(api_client: TestClient) -> None:
    tables = generate_tables(GeneratorConfig(seed=32, n_customers=18))
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("pack/metadata.json", "{}")
        for name, frame in tables.items():
            archive.writestr(f"pack/{name}.csv", frame.to_csv(index=False))
    response = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("merchant-pack.zip", buffer.getvalue(), "application/zip"))],
    )
    assert response.status_code == 200, response.text
    assert response.json()["customer_count"] == 18
    assert response.json()["validation_status"] == "ok"


def test_valid_xlsx_upload(api_client: TestClient) -> None:
    tables = generate_tables(GeneratorConfig(seed=22, n_customers=20))
    files = []
    for name, frame in tables.items():
        buffer = BytesIO()
        frame.to_excel(buffer, index=False)
        files.append(
            (
                "files",
                (f"{name}.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            )
        )
    response = api_client.post("/api/v1/data/upload", files=files)
    assert response.status_code == 200, response.text
    payload = DatasetSummary.model_validate(response.json())
    assert payload.validation_status == "ok"
    assert payload.customer_count == 20


def test_unsupported_upload(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert response.status_code in {400, 415}
    assert "error" in response.json()


def test_invalid_dataset_schema(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("revenue_events.csv", b"event_id\nEVT_1\n", "text/csv"))],
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"VALIDATION_FAILURE", "DATASET_LOAD_FAILED"}


def test_malformed_request(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    event_id = _open_event_id(tables)
    response = api_client.post(
        f"/api/v1/events/{event_id}/agent/run",
        json={"force_recompute": "definitely-not-a-bool"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_structured_unknown_route(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.json()
    assert "code" in response.json()["error"]


def test_openapi_available(api_client: TestClient) -> None:
    response = api_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/opportunities" in paths
    assert "/api/v1/events/{event_id}/agent/run" in paths
    assert "/api/v1/agent/activity" in paths
    assert "/api/v1/agent/health" in paths
    assert "/api/v1/metrics/outcomes" in paths
    assert "/api/v1/metrics/actions" in paths
    assert "/api/v1/metrics/segments" in paths
    assert "/api/v1/metrics/dashboard" in paths
    assert "/api/v1/copilot/ask" in paths


def test_opportunity_and_event_detail_are_consistent(api_client: TestClient) -> None:
    listed = api_client.get("/api/v1/opportunities", params={"limit": 1, "status": "open"}).json()
    item = listed["items"][0]
    detail = api_client.get(f"/api/v1/events/{item['event_id']}").json()
    risk = detail["risk_assessment"]
    assert risk["event_id"] == item["event_id"]
    assert risk["customer_id"] == item["customer_id"]
    assert risk["amount_at_risk"] == item["amount_at_risk"]
    assert risk["recovery_probability"] == item["recovery_probability"]
    assert risk["churn_probability"] == item["churn_probability"]
    assert risk["expected_recovery_value"] == item["expected_recovery_value"]
    assert risk["priority_category"] == item["priority_category"]
    assert abs(risk["priority_score"] - item["priority_score"]) < 1e-6


def test_agent_activity_after_run(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    empty = api_client.get("/api/v1/agent/activity")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    event_id = _open_event_id(tables)
    run = api_client.post(f"/api/v1/events/{event_id}/agent/run", json={})
    assert run.status_code == 200
    activity = api_client.get("/api/v1/agent/activity").json()
    assert activity["total"] >= 1
    assert activity["items"][0]["event_id"] == event_id
    assert activity["items"][0]["workflow_id"] == run.json()["workflow_id"]
    assert activity["items"][0]["selected_action"] == run.json()["selected_action"]["action_type"]
    assert activity["items"][0]["guardrail_status"] == run.json()["guardrail_result"]["status"]


def test_outcome_metrics_empty_then_populated(api_client: TestClient, tables: dict[str, pd.DataFrame]) -> None:
    empty = api_client.get("/api/v1/metrics/outcomes")
    assert empty.status_code == 200
    assert empty.json()["executions"] == 0
    assert empty.json()["recovery_rate"] is None
    event_id = _open_event_id(tables)
    api_client.post(f"/api/v1/events/{event_id}/agent/run", json={})
    outcomes = api_client.get("/api/v1/metrics/outcomes")
    assert outcomes.status_code == 200
    body = outcomes.json()
    assert body["executions"] >= 1
    assert "agent_workflows" == body["source"]
    assert "ground-truth" in body["disclaimer"].lower() or "ground-truth" in body["disclaimer"]
    actions = api_client.get("/api/v1/metrics/actions")
    assert actions.status_code == 200
    assert isinstance(actions.json()["items"], list)
    segments = api_client.get("/api/v1/metrics/segments")
    assert segments.status_code == 200
    assert "learning_signals" in segments.json()
    filtered = api_client.get("/api/v1/metrics/actions", params={"action_type": "does_not_exist"})
    assert filtered.status_code == 200
    assert filtered.json()["items"] == []
