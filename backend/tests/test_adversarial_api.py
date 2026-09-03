from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_runtime
from app.core.config import get_settings
from app.main import app
from app.schemas.api import AgentRunRequest
from app.services.agent_runs import list_agent_activity, persist_workflow, run_event_agent
from app.services.data.synthetic import GeneratorConfig, generate_tables
from app.services.outcomes import aggregate_outcomes, load_outcome_records
from app.services.persistence import append_jsonl
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


def _open_event_id(runtime: AppRuntime) -> str:
    events = runtime.tables()["revenue_events"]
    open_events = events[events["event_status"].astype(str).str.lower() == "open"]
    return str(open_events.iloc[0]["event_id"])


def test_health_and_structured_404(api_client: TestClient) -> None:
    assert api_client.get("/health").json()["status"] == "healthy"
    missing = api_client.get("/api/v1/events/EVT_NOPE")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "EVENT_NOT_FOUND"
    assert "traceback" not in missing.text.lower()
    assert "/Users/" not in missing.text


def test_malformed_json_body(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _open_event_id(runtime)
    response = api_client.post(
        f"/api/v1/events/{event_id}/agent/run",
        content="{not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_dry_run_does_not_persist(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _open_event_id(runtime)
    response = api_client.post(
        f"/api/v1/events/{event_id}/agent/run",
        json={"dry_run": True},
    )
    assert response.status_code == 200
    assert response.json()["dry_run"] is True
    latest = api_client.get(f"/api/v1/events/{event_id}/agent/latest")
    assert latest.status_code == 404
    activity = api_client.get("/api/v1/agent/activity")
    assert activity.json()["total"] == 0


def test_repeated_run_respects_cooldown(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _open_event_id(runtime)
    first = api_client.post(f"/api/v1/events/{event_id}/agent/run", json={})
    assert first.status_code == 200
    assert first.json()["guardrail_result"]["status"] in {"ALLOW", "BLOCK"}
    second = api_client.post(f"/api/v1/events/{event_id}/agent/run", json={})
    assert second.status_code == 200
    if first.json()["guardrail_result"]["allowed"] and first.json()["execution_result"]:
        assert second.json()["guardrail_result"]["allowed"] is False
        assert second.json().get("execution_result") is None
        assert second.json()["outcome"]["outcome"] == "BLOCKED"


def test_agent_response_has_no_langgraph_internals(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _open_event_id(runtime)
    payload = api_client.post(f"/api/v1/events/{event_id}/agent/run", json={}).json()
    assert "next_step" not in payload
    assert "event_context" not in payload
    assert "iteration" not in payload


def test_corrupt_latest_json_does_not_crash_activity(runtime: AppRuntime) -> None:
    event_id = _open_event_id(runtime)
    result = run_event_agent(runtime, event_id, AgentRunRequest())
    persist_workflow(runtime, result)
    latest = runtime.workflows_dir / event_id / "latest.json"
    latest.write_text("{truncated", encoding="utf-8")
    history = runtime.workflows_dir / event_id / "history.jsonl"
    append_jsonl(history, {"not": "a workflow"})
    activity = list_agent_activity(runtime)
    assert activity.total >= 0
    metrics = aggregate_outcomes(load_outcome_records(runtime))
    assert metrics.executions >= 0


def test_corrupt_latest_returns_structured_error(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _open_event_id(runtime)
    api_client.post(f"/api/v1/events/{event_id}/agent/run", json={})
    path = runtime.workflows_dir / event_id / "latest.json"
    path.write_text("{bad", encoding="utf-8")
    response = api_client.get(f"/api/v1/events/{event_id}/agent/latest")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "WORKFLOW_CORRUPT"


def test_metrics_never_mix_dataset_labels(api_client: TestClient, runtime: AppRuntime) -> None:
    summary = api_client.get("/api/v1/data/summary").json()
    outcomes = api_client.get("/api/v1/metrics/outcomes").json()
    overview = api_client.get("/api/v1/metrics/overview").json()
    assert outcomes["executions"] != summary["recovered_event_count"] or outcomes["executions"] == 0
    assert overview["dataset"]["recovered_event_count"] == summary["recovered_event_count"]
    assert "ground-truth" in outcomes["disclaimer"].lower() or "ground-truth" in outcomes["disclaimer"]


def test_unknown_query_params_do_not_500(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/opportunities", params={"limit": 1, "made_up": "yes"})
    assert response.status_code == 200


def test_empty_metrics_and_activity(api_client: TestClient) -> None:
    assert api_client.get("/api/v1/metrics/actions").json()["items"] == []
    assert api_client.get("/api/v1/metrics/segments").json()["learning_signals"] == []
    assert api_client.get("/api/v1/agent/activity").json()["total"] == 0
