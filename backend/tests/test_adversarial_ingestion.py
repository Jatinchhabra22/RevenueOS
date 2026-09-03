from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_runtime
from app.core.config import get_settings
from app.core.risk_config import RiskEngineConfig, load_risk_config
from app.main import app
from app.services.data.loaders import IngestionError, load_directory, load_table
from app.services.data.synthetic import GeneratorConfig, generate_tables
from app.services.data.validation import REQUIRED_COLUMNS, validate_dataset
from app.services.risk.engine import _priority_category
from app.services.runtime import AppRuntime


def _write_csv(directory: Path, tables: dict[str, pd.DataFrame]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


def _empty(table: str) -> pd.DataFrame:
    return pd.DataFrame(columns=REQUIRED_COLUMNS[table])


def _events_only() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": ["EVT_1"],
            "event_timestamp": ["2026-08-01T10:00:00"],
            "merchant_id": ["MERCHANT_001"],
            "customer_id": ["CUS_1"],
            "event_type": ["payment_failed"],
            "amount_at_risk": [500],
            "event_status": ["open"],
        }
    )


def test_empty_csv_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "revenue_events.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(IngestionError, match="empty"):
        load_table(path)


def test_extra_columns_are_ignored(tmp_path: Path) -> None:
    frame = _events_only()
    frame["totally_unexpected"] = ["x"]
    path = tmp_path / "revenue_events.csv"
    frame.to_csv(path, index=False)
    _, loaded, _ = load_table(path)
    assert "event_id" in loaded.columns
    assert "totally_unexpected" in loaded.columns


def test_duplicate_columns_do_not_crash(tmp_path: Path) -> None:
    path = tmp_path / "revenue_events.csv"
    path.write_text(
        "event_id,event_timestamp,merchant_id,customer_id,event_type,amount_at_risk,event_status,event_id\n"
        "EVT_1,2026-08-01T10:00:00,M,C,payment_failed,100,open,EVT_DUP\n",
        encoding="utf-8",
    )
    _, loaded, _ = load_table(path)
    assert list(loaded.columns).count("event_id") == 1


def test_invalid_and_nonfinite_amounts_are_rejected() -> None:
    events = _events_only()
    events["amount_at_risk"] = ["₹500"]
    report = validate_dataset(
        pd.DataFrame({"customer_id": ["CUS_1"], "merchant_id": ["M"], "signup_date": ["2026-01-01"]}),
        _empty("transactions"),
        _empty("subscriptions"),
        events,
        _empty("intervention_history"),
    )
    assert report["ok"] is False
    assert any("amount_at_risk" in item for item in report["errors"])

    events = _events_only()
    events["amount_at_risk"] = [float("inf")]
    report = validate_dataset(
        pd.DataFrame({"customer_id": ["CUS_1"], "merchant_id": ["M"], "signup_date": ["2026-01-01"]}),
        _empty("transactions"),
        _empty("subscriptions"),
        events,
        _empty("intervention_history"),
    )
    assert report["ok"] is False
    assert any("non-finite" in item for item in report["errors"])


def test_negative_and_duplicate_ids() -> None:
    customers = pd.DataFrame(
        {"customer_id": ["CUS_1", "CUS_1"], "merchant_id": ["M", "M"], "signup_date": ["2026-01-01", "2026-01-01"]}
    )
    events = pd.DataFrame(
        {
            "event_id": ["EVT_1", "EVT_1"],
            "event_timestamp": ["2026-08-01T10:00:00", "2026-08-01T10:00:00"],
            "merchant_id": ["M", "M"],
            "customer_id": ["CUS_1", "CUS_1"],
            "event_type": ["payment_failed", "payment_failed"],
            "amount_at_risk": [-10, 10],
            "event_status": ["open", "open"],
        }
    )
    report = validate_dataset(
        customers,
        _empty("transactions"),
        _empty("subscriptions"),
        events,
        _empty("intervention_history"),
    )
    assert report["ok"] is False
    assert "duplicate customer_id" in report["errors"]
    assert "duplicate event_id" in report["errors"]
    assert any("negative" in item for item in report["errors"])


def test_unrelated_csv_is_skipped(tmp_path: Path) -> None:
    (tmp_path / "notes.csv").write_text("hello,world\n1,2\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="revenue_events"):
        load_directory(tmp_path)


def test_priority_boundaries() -> None:
    config = RiskEngineConfig()
    assert _priority_category(70.0, config) == "CRITICAL"
    assert _priority_category(69.999, config) == "HIGH"
    assert _priority_category(50.0, config) == "HIGH"
    assert _priority_category(49.999, config) == "MEDIUM"
    assert _priority_category(30.0, config) == "MEDIUM"
    assert _priority_category(29.999, config) == "LOW"
    assert _priority_category(0.0, config) == "LOW"


def test_malformed_risk_config_is_explicit(tmp_path: Path) -> None:
    path = tmp_path / "risk_engine.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="not valid JSON"):
        load_risk_config(path)


def test_invalid_risk_weights_are_rejected() -> None:
    with pytest.raises(ValueError):
        RiskEngineConfig(weight_expected_recovery=1, weight_customer_value=1, weight_churn_risk=1, weight_urgency=1)


@pytest.fixture
def api_client(tmp_path: Path) -> TestClient:
    tables = generate_tables(GeneratorConfig(seed=11, n_customers=40))
    active = tmp_path / "data" / "demo"
    _write_csv(active, tables)
    settings = get_settings()
    runtime = AppRuntime(
        data_dir=tmp_path / "data",
        artifacts_dir=settings.artifacts_path,
        models_dir=settings.models_path,
        uploads_dir=tmp_path / "data" / "uploads",
        workflows_dir=tmp_path / "artifacts" / "workflows",
        active_dataset_dir=active,
        upload_max_bytes=2_000,
        disable_llm=True,
    )
    app.dependency_overrides[get_runtime] = lambda: runtime
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


def test_upload_rejects_path_traversal_filename(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("../../evil.csv", b"event_id\n1\n", "text/csv"))],
    )
    assert response.status_code in {400, 415, 422}
    assert "error" in response.json()
    assert "traceback" not in response.text.lower()


def test_upload_rejects_exe_and_empty(api_client: TestClient) -> None:
    exe = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("data.csv.exe", b"x", "application/octet-stream"))],
    )
    assert exe.status_code == 415
    empty = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("revenue_events.csv", b"", "text/csv"))],
    )
    assert empty.status_code == 400


def test_upload_rejects_oversized_file(api_client: TestClient) -> None:
    payload = b"x" * 3000
    response = api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("revenue_events.csv", payload, "text/csv"))],
    )
    assert response.status_code == 413
    body = response.json()
    assert body["error"]["code"] == "INVALID_REQUEST"


def test_failed_upload_does_not_replace_active_dataset(api_client: TestClient) -> None:
    before = api_client.get("/api/v1/data/summary").json()
    api_client.post(
        "/api/v1/data/upload",
        files=[("files", ("revenue_events.csv", b"event_id\nEVT_1\n", "text/csv"))],
    )
    after = api_client.get("/api/v1/data/summary").json()
    assert after["dataset_id"] == before["dataset_id"]
    assert after["revenue_event_count"] == before["revenue_event_count"]


def test_xlsx_empty_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "revenue_events.xlsx"
    pd.DataFrame().to_excel(path, index=False)
    with pytest.raises(IngestionError, match="empty"):
        load_table(path)
