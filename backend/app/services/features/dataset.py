"""Build labeled feature matrices from canonical tables.

Recovery labels come from intervention outcomes. Feature rows are computed as-of
the event timestamp and exclude the current event's recovery result.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import pandas as pd

from app.schemas.entities import Transaction
from app.services.features.churn_features import churn_feature_dict, churn_feature_frame
from app.services.features.feature_utils import as_datetime, to_float
from app.services.features.recovery_features import recovery_feature_dict, recovery_feature_frame


def _txn_models(frame: pd.DataFrame) -> dict[str, list[Transaction]]:
    grouped: dict[str, list[Transaction]] = defaultdict(list)
    if frame.empty:
        return grouped
    records = frame.to_dict(orient="records")
    for row in records:
        cleaned = {key: (None if pd.isna(value) else value) for key, value in row.items()}
        try:
            model = Transaction.model_validate(cleaned)
        except Exception:
            continue
        grouped[str(model.customer_id)].append(model)
    return grouped


def build_recovery_training_set(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    events = tables["revenue_events"].copy()
    customers = tables.get("customers", pd.DataFrame())
    subscriptions = tables.get("subscriptions", pd.DataFrame())
    interventions = tables.get("intervention_history", pd.DataFrame())
    transactions = tables.get("transactions", pd.DataFrame())

    recovered_events: set[str] = set()
    if not interventions.empty:
        recovered_events = set(
            interventions.loc[interventions["outcome"].astype(str) == "recovered", "event_id"].astype(str)
        )
        labeled_ids = set(interventions["event_id"].astype(str))
        events = events[events["event_id"].astype(str).isin(labeled_ids)].copy()

    customer_by_id = (
        customers.set_index(customers["customer_id"].astype(str)).to_dict(orient="index") if not customers.empty else {}
    )
    sub_by_id = (
        subscriptions.set_index(subscriptions["subscription_id"].astype(str)).to_dict(orient="index")
        if not subscriptions.empty and "subscription_id" in subscriptions.columns
        else {}
    )
    sub_by_customer: dict = {}
    if not subscriptions.empty:
        deduped = subscriptions.drop_duplicates("customer_id")
        sub_by_customer = deduped.set_index(deduped["customer_id"].astype(str)).to_dict(orient="index")
    txns_by_customer = _txn_models(transactions)

    recoveries_before: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    if not events.empty:
        for row in events.itertuples(index=False):
            eid = str(row.event_id)
            if eid not in recovered_events:
                continue
            ts = as_datetime(row.event_timestamp)
            if ts is None:
                continue
            recoveries_before[str(row.customer_id)].append((ts, eid))

    rows: list[dict] = []
    labels: list[int] = []
    ids: list[str] = []

    for row in events.itertuples(index=False):
        event_id = str(row.event_id)
        customer_id = str(row.customer_id)
        as_of = as_datetime(row.event_timestamp)
        customer = customer_by_id.get(customer_id, {})
        subscription = {}
        sub_id = str(getattr(row, "subscription_id", "") or "")
        if sub_id and sub_id in sub_by_id:
            subscription = sub_by_id[sub_id]
        else:
            subscription = sub_by_customer.get(customer_id, {})

        prior_recoveries = 0
        for ts, other_id in recoveries_before.get(customer_id, []):
            if other_id == event_id:
                continue
            if as_of is None or ts <= as_of:
                prior_recoveries += 1

        is_recurring = bool(sub_id) or bool(getattr(row, "event_type", "") == "subscription_payment_failed")
        features = recovery_feature_dict(
            amount_at_risk=row.amount_at_risk,
            attempt_number=getattr(row, "attempt_number", 1),
            failure_reason=getattr(row, "failure_reason", None),
            payment_method=getattr(row, "payment_method", None),
            event_type=row.event_type,
            urgency=getattr(row, "urgency", None),
            event_timestamp=row.event_timestamp,
            is_recurring=is_recurring,
            tenure_days=customer.get("tenure_days"),
            engagement_score=customer.get("engagement_score"),
            activity_trend=customer.get("activity_trend"),
            customer_segment=customer.get("customer_segment"),
            previous_recoveries=prior_recoveries,
            failed_cycles=subscription.get("failed_cycles", 0),
            transactions=txns_by_customer.get(customer_id, []),
            fallback_payment_success_rate=customer.get("payment_success_rate"),
            fallback_previous_failures=customer.get("previous_failures"),
            fallback_last_activity=customer.get("last_activity_date"),
        )
        rows.append(features)
        labels.append(1 if event_id in recovered_events else 0)
        ids.append(event_id)

    X = recovery_feature_frame(rows)
    y = pd.Series(labels, name="target_recovered")
    event_ids = pd.Series(ids, name="event_id")
    return X, y, event_ids


def build_churn_training_set(
    tables: dict[str, pd.DataFrame],
    as_of: datetime | None = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    customers = tables["customers"].copy()
    subscriptions = tables.get("subscriptions", pd.DataFrame())
    transactions = tables.get("transactions", pd.DataFrame())
    if "churned" not in customers.columns:
        raise ValueError("customers.churned is required to train the churn model")

    sub_by_customer: dict = {}
    if not subscriptions.empty:
        deduped = subscriptions.drop_duplicates("customer_id")
        sub_by_customer = deduped.set_index(deduped["customer_id"].astype(str)).to_dict(orient="index")
    txns_by_customer = _txn_models(transactions)
    if as_of is None:
        as_of = datetime(2026, 9, 1)

    rows: list[dict] = []
    labels: list[int] = []
    ids: list[str] = []
    for row in customers.itertuples(index=False):
        customer_id = str(row.customer_id)
        subscription = sub_by_customer.get(customer_id, {})
        recent_failures = 0.0
        for txn in txns_by_customer.get(customer_id, []):
            if str(txn.transaction_status).lower() != "failed":
                continue
            ts = as_datetime(txn.transaction_timestamp)
            if ts is None:
                continue
            age = (as_of - ts).total_seconds() / 86400.0
            if 0 <= age <= 45:
                recent_failures += 1
        features = churn_feature_dict(
            tenure_days=getattr(row, "tenure_days", None),
            total_spend=getattr(row, "total_spend", None),
            customer_ltv=getattr(row, "customer_ltv", None),
            engagement_score=getattr(row, "engagement_score", None),
            payment_success_rate=getattr(row, "payment_success_rate", None),
            previous_failures=getattr(row, "previous_failures", 0),
            previous_recoveries=getattr(row, "previous_recoveries", 0),
            failed_cycles=subscription.get("failed_cycles", 0),
            avg_order_value=getattr(row, "avg_order_value", None),
            total_orders=getattr(row, "total_orders", None),
            activity_trend=getattr(row, "activity_trend", None),
            customer_segment=getattr(row, "customer_segment", None),
            has_subscription=bool(subscription),
            last_activity=getattr(row, "last_activity_date", None),
            as_of=as_of,
            recent_payment_failures=recent_failures,
        )
        rows.append(features)
        labels.append(int(to_float(getattr(row, "churned"), default=0) or 0))
        ids.append(customer_id)

    X = churn_feature_frame(rows)
    y = pd.Series(labels, name="target_churned")
    customer_ids = pd.Series(ids, name="customer_id")
    return X, y, customer_ids
