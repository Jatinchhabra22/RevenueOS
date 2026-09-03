"""File loading, alias application, type coercion, and dataset assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.services.data.aliases import apply_column_aliases, canonical_table_name
from app.services.data.validation import REQUIRED_COLUMNS, validate_dataset

SUPPORTED_SUFFIXES = {".csv", ".xlsx"}

DATETIME_COLUMNS = {
    "signup_date",
    "last_activity_date",
    "transaction_timestamp",
    "subscription_start_date",
    "next_billing_date",
    "event_timestamp",
    "action_timestamp",
}

NUMERIC_COLUMNS = {
    "tenure_days",
    "total_orders",
    "total_spend",
    "avg_order_value",
    "payment_success_rate",
    "previous_failures",
    "previous_recoveries",
    "engagement_score",
    "customer_ltv",
    "churned",
    "amount",
    "attempt_number",
    "recurring_amount",
    "successful_cycles",
    "failed_cycles",
    "amount_at_risk",
    "amount_recovered",
    "response_time_hours",
}

BOOL_COLUMNS = {"is_recurring"}


class IngestionError(ValueError):
    pass


def _read_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise IngestionError(f"Unsupported format '{suffix}'. Use CSV or XLSX.")
    if suffix == ".csv":
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError as exc:
            raise IngestionError("Uploaded table is empty") from exc
    else:
        frame = pd.read_excel(path)
    if frame.empty:
        raise IngestionError("Uploaded table is empty")
    return frame


def _normalize_strings(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if result[column].dtype == object:
            result[column] = result[column].map(
                lambda value: value.strip().lower()
                if isinstance(value, str) and column in {"transaction_status", "event_status", "activity_trend"}
                else (value.strip() if isinstance(value, str) else value)
            )
    return result


def _coerce_types(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.columns:
        if column in DATETIME_COLUMNS:
            result[column] = pd.to_datetime(result[column], errors="coerce")
        elif column in NUMERIC_COLUMNS:
            result[column] = pd.to_numeric(result[column], errors="coerce")
        elif column in BOOL_COLUMNS:
            result[column] = result[column].map(
                lambda value: value
                if isinstance(value, bool)
                else str(value).strip().lower() in {"1", "true", "yes"}
                if pd.notna(value) and str(value).strip() != ""
                else False
            )
    return result


def load_table(path: Path, table: str | None = None) -> tuple[str, pd.DataFrame, dict[str, str]]:
    inferred = table or canonical_table_name(path.name)
    if inferred is None:
        raise IngestionError(
            f"Could not infer table type from '{path.name}'. "
            "Name the file customers, transactions, subscriptions, revenue_events, or intervention_history."
        )
    frame = _read_file(path)
    new_names, applied = apply_column_aliases(inferred, [str(c) for c in frame.columns])
    frame.columns = new_names
    # Drop duplicate canonical columns created by alias collisions, keep first
    frame = frame.loc[:, ~pd.Index(frame.columns).duplicated()]
    frame = _normalize_strings(frame)
    frame = _coerce_types(frame)
    missing = [col for col in REQUIRED_COLUMNS[inferred] if col not in frame.columns]
    if missing:
        raise IngestionError(f"{inferred} is missing required columns: {missing}")
    return inferred, frame, applied


def load_directory(directory: Path) -> dict[str, Any]:
    directory = Path(directory)
    if not directory.exists():
        raise IngestionError("Directory not found")

    tables: dict[str, pd.DataFrame] = {}
    mappings: dict[str, dict[str, str]] = {}
    files_loaded: list[str] = []

    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if canonical_table_name(path.name) is None:
            continue
        name, frame, applied = load_table(path)
        tables[name] = frame
        mappings[name] = applied
        files_loaded.append(path.name)

    if "revenue_events" not in tables:
        found = ", ".join(files_loaded) if files_loaded else "no table files"
        raise IngestionError(
            "A revenue events file is required (revenue_events.csv or revenue_events.xlsx). "
            f"Loaded: {found}. Upload all five CSVs from one pack folder, or a zip of that folder."
        )

    empty = pd.DataFrame()
    report = validate_dataset(
        tables.get("customers", empty),
        tables.get("transactions", empty),
        tables.get("subscriptions", empty),
        tables["revenue_events"],
        tables.get("intervention_history", empty),
    )
    report["column_mappings"] = mappings
    report["files_loaded"] = files_loaded
    return {"tables": tables, "report": report}
