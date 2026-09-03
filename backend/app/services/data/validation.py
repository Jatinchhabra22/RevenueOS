"""Quality checks for synthetic and ingested merchant datasets."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS: dict[str, list[str]] = {
    "customers": [
        "customer_id",
        "merchant_id",
        "signup_date",
    ],
    "transactions": [
        "transaction_id",
        "customer_id",
        "merchant_id",
        "transaction_timestamp",
        "amount",
        "currency",
        "payment_method",
        "transaction_status",
    ],
    "subscriptions": [
        "subscription_id",
        "customer_id",
        "merchant_id",
        "subscription_start_date",
        "subscription_status",
        "recurring_amount",
        "billing_frequency",
    ],
    "revenue_events": [
        "event_id",
        "event_timestamp",
        "merchant_id",
        "customer_id",
        "event_type",
        "amount_at_risk",
        "event_status",
    ],
    "intervention_history": [
        "intervention_id",
        "event_id",
        "customer_id",
        "action_type",
        "action_timestamp",
        "attempt_number",
        "outcome",
    ],
}


def _duplicate_ids(frame: pd.DataFrame, column: str) -> int:
    if frame.empty:
        return 0
    return int(frame[column].duplicated().sum())


def validate_dataset(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    subscriptions: pd.DataFrame,
    revenue_events: pd.DataFrame,
    intervention_history: pd.DataFrame,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    tables = {
        "customers": customers,
        "transactions": transactions,
        "subscriptions": subscriptions,
        "revenue_events": revenue_events,
        "intervention_history": intervention_history,
    }

    for name, frame in tables.items():
        missing = [col for col in REQUIRED_COLUMNS[name] if col not in frame.columns]
        if missing:
            errors.append(f"{name} missing columns: {missing}")

    if errors:
        return {
            "ok": False,
            "errors": errors,
            "warnings": warnings,
            "row_counts": {k: int(len(v)) for k, v in tables.items()},
        }

    if _duplicate_ids(customers, "customer_id"):
        errors.append("duplicate customer_id")
    if _duplicate_ids(transactions, "transaction_id"):
        errors.append("duplicate transaction_id")
    if _duplicate_ids(subscriptions, "subscription_id"):
        errors.append("duplicate subscription_id")
    if _duplicate_ids(revenue_events, "event_id"):
        errors.append("duplicate event_id")
    if _duplicate_ids(intervention_history, "intervention_id"):
        errors.append("duplicate intervention_id")

    customer_ids = set(customers["customer_id"].astype(str))
    txn_ids = set(transactions["transaction_id"].astype(str))
    sub_ids = set(subscriptions["subscription_id"].astype(str))
    event_ids = set(revenue_events["event_id"].astype(str))

    orphan_txn = ~transactions["customer_id"].astype(str).isin(customer_ids)
    if int(orphan_txn.sum()):
        errors.append("transactions with unknown customer_id")

    orphan_sub = ~subscriptions["customer_id"].astype(str).isin(customer_ids)
    if int(orphan_sub.sum()):
        errors.append("subscriptions with unknown customer_id")

    orphan_evt_cust = ~revenue_events["customer_id"].astype(str).isin(customer_ids)
    if int(orphan_evt_cust.sum()):
        errors.append("revenue_events with unknown customer_id")

    if "transaction_id" in revenue_events.columns:
        linked_txn = revenue_events["transaction_id"].notna() & (
            revenue_events["transaction_id"].astype(str) != ""
        )
        missing_txn = linked_txn & ~revenue_events["transaction_id"].astype(str).isin(txn_ids)
        if int(missing_txn.sum()):
            errors.append("revenue_events.transaction_id not found")

    if "subscription_id" in revenue_events.columns:
        linked_sub = revenue_events["subscription_id"].notna() & (
            revenue_events["subscription_id"].astype(str) != ""
        )
        missing_sub = linked_sub & ~revenue_events["subscription_id"].astype(str).isin(sub_ids)
        if int(missing_sub.sum()):
            errors.append("revenue_events.subscription_id not found")

    orphan_int = ~intervention_history["event_id"].astype(str).isin(event_ids)
    if int(orphan_int.sum()):
        errors.append("intervention_history with unknown event_id")

    for name, column in (
        ("customers", "customer_id"),
        ("transactions", "transaction_id"),
        ("subscriptions", "subscription_id"),
        ("revenue_events", "event_id"),
        ("intervention_history", "intervention_id"),
    ):
        frame = tables[name]
        if frame.empty or column not in frame.columns:
            continue
        stripped = frame[column].astype(str).str.strip()
        if bool((stripped.eq("") | stripped.str.lower().isin(["nan", "none", "null"])).any()):
            errors.append(f"blank {column} in {name}")

    for col, frame in (
        ("amount", transactions),
        ("amount_at_risk", revenue_events),
        ("recurring_amount", subscriptions),
        ("customer_ltv", customers),
        ("payment_success_rate", customers),
    ):
        if col not in frame.columns or frame.empty:
            continue
        series = pd.to_numeric(frame[col], errors="coerce")
        required = col in {"amount", "amount_at_risk", "recurring_amount"}
        finite = np.isfinite(series.to_numpy(dtype="float64", na_value=np.nan))
        if required and not bool(np.all(finite)):
            errors.append(f"non-finite or invalid numeric values in {col}")
        elif not required:
            present = frame[col].notna() & (frame[col].astype(str).str.strip() != "")
            if bool((present.to_numpy() & ~finite).any()):
                errors.append(f"non-finite or invalid numeric values in {col}")
        if bool((series < 0).any()):
            errors.append(f"negative values in {col}")
        if col == "payment_success_rate" and bool((series > 1.0).any()):
            errors.append("payment_success_rate must be between 0 and 1")

    recovered = intervention_history["outcome"].eq("recovered")
    if "amount_recovered" in intervention_history.columns:
        recovered_amt = intervention_history.loc[recovered, "amount_recovered"].fillna(0)
        if bool((recovered_amt < 0).any()):
            errors.append("negative amount_recovered")

    recovery_rate = float(recovered.mean()) if len(intervention_history) else 0.0
    churn_rate = float(customers["churned"].mean()) if "churned" in customers.columns else 0.0

    if not (0.30 <= recovery_rate <= 0.60):
        warnings.append(f"recovery rate {recovery_rate:.3f} outside 0.30–0.60 target band")
    if not (0.08 <= churn_rate <= 0.35):
        warnings.append(f"churn rate {churn_rate:.3f} outside 0.10–0.30 target band")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "row_counts": {k: int(len(v)) for k, v in tables.items()},
        "recovery_rate": recovery_rate,
        "churn_rate": churn_rate,
        "failure_reason_distribution": (
            transactions["failure_reason"].value_counts(dropna=True).to_dict()
            if "failure_reason" in transactions.columns
            else {}
        ),
    }
