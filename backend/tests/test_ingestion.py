from pathlib import Path

import pandas as pd
import pytest

from app.services.data.context import assemble_event_context
from app.services.data.loaders import IngestionError, load_directory, load_table
from app.services.data.synthetic import GeneratorConfig, generate_tables


def _write_tables(directory: Path, tables: dict[str, pd.DataFrame]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


def test_csv_directory_ingestion(tmp_path: Path) -> None:
    tables = generate_tables(GeneratorConfig(seed=3, n_customers=40))
    _write_tables(tmp_path, tables)
    result = load_directory(tmp_path)
    assert "revenue_events" in result["tables"]
    assert result["report"]["ok"] or result["report"]["row_counts"]["revenue_events"] > 0


def test_xlsx_and_aliases(tmp_path: Path) -> None:
    events = pd.DataFrame(
        {
            "id": ["EVT_1"],
            "timestamp": ["2026-08-01T10:00:00"],
            "merchant_id": ["MERCHANT_001"],
            "user_id": ["CUS_1"],
            "type": ["payment_failed"],
            "amount": [1999],
            "status": ["open"],
        }
    )
    path = tmp_path / "events.xlsx"
    events.to_excel(path, index=False)
    name, frame, applied = load_table(path)
    assert name == "revenue_events"
    assert "event_id" in frame.columns
    assert "amount_at_risk" in frame.columns
    assert applied["user_id"] == "customer_id"
    assert applied["amount"] == "amount_at_risk"


def test_invalid_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("nope", encoding="utf-8")
    with pytest.raises(IngestionError):
        load_table(path, table="revenue_events")


def test_missing_required_columns(tmp_path: Path) -> None:
    path = tmp_path / "revenue_events.csv"
    pd.DataFrame({"event_id": ["EVT_1"]}).to_csv(path, index=False)
    with pytest.raises(IngestionError, match="missing required columns"):
        load_table(path)


def test_event_context_assembly(tmp_path: Path) -> None:
    tables = generate_tables(GeneratorConfig(seed=9, n_customers=60))
    _write_tables(tmp_path, tables)
    loaded = load_directory(tmp_path)["tables"]
    event_id = str(loaded["revenue_events"].iloc[0]["event_id"])
    context = assemble_event_context(event_id, loaded)
    assert context.event.event_id == event_id
    assert context.customer is not None
    assert context.customer.customer_id == context.event.customer_id


def test_missing_optional_customer_does_not_crash(tmp_path: Path) -> None:
    events = pd.DataFrame(
        {
            "event_id": ["EVT_9"],
            "event_timestamp": ["2026-08-01T10:00:00"],
            "merchant_id": ["MERCHANT_001"],
            "customer_id": ["CUS_MISSING"],
            "event_type": ["payment_failed"],
            "amount_at_risk": [500],
            "event_status": ["open"],
        }
    )
    path = tmp_path / "revenue_events.csv"
    events.to_csv(path, index=False)
    tables = load_directory(tmp_path)["tables"]
    context = assemble_event_context("EVT_9", tables)
    assert context.customer is None
    assert context.event.amount_at_risk == 500
