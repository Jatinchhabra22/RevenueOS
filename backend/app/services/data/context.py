"""Assemble EventContext from canonical tables."""

from __future__ import annotations

import pandas as pd

from app.schemas.entities import (
    Customer,
    EventContext,
    Intervention,
    RevenueEvent,
    Subscription,
    Transaction,
)


def _row_or_none(frame: pd.DataFrame, column: str, value: str | None) -> dict | None:
    if not value or frame.empty or column not in frame.columns:
        return None
    matched = frame[frame[column].astype(str) == str(value)]
    if matched.empty:
        return None
    return matched.iloc[0].to_dict()


def _records(frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _safe_model(model_cls, payload: dict | None):
    if not payload:
        return None
    cleaned = {key: (None if pd.isna(value) else value) for key, value in payload.items()}
    return model_cls.model_validate(cleaned)


def assemble_event_context(
    event_id: str,
    tables: dict[str, pd.DataFrame],
    recent_transaction_limit: int = 20,
) -> EventContext:
    events = tables.get("revenue_events")
    if events is None or events.empty:
        raise ValueError("No revenue events available")

    event_row = _row_or_none(events, "event_id", event_id)
    if event_row is None:
        raise ValueError(f"Unknown event_id: {event_id}")

    event = _safe_model(RevenueEvent, event_row)
    customer_id = event.customer_id

    customer = _safe_model(
        Customer,
        _row_or_none(tables.get("customers", pd.DataFrame()), "customer_id", customer_id),
    )
    subscription = _safe_model(
        Subscription,
        _row_or_none(
            tables.get("subscriptions", pd.DataFrame()),
            "subscription_id",
            event.subscription_id,
        )
        or _row_or_none(tables.get("subscriptions", pd.DataFrame()), "customer_id", customer_id),
    )
    related_transaction = _safe_model(
        Transaction,
        _row_or_none(
            tables.get("transactions", pd.DataFrame()),
            "transaction_id",
            event.transaction_id,
        ),
    )

    txns = tables.get("transactions", pd.DataFrame())
    recent: list[Transaction] = []
    if not txns.empty and "customer_id" in txns.columns:
        subset = txns[txns["customer_id"].astype(str) == str(customer_id)].copy()
        if "transaction_timestamp" in subset.columns:
            subset = subset.sort_values("transaction_timestamp", ascending=False)
        for payload in _records(subset.head(recent_transaction_limit)):
            model = _safe_model(Transaction, payload)
            if model:
                recent.append(model)

    history = tables.get("intervention_history", pd.DataFrame())
    previous: list[Intervention] = []
    if not history.empty and "event_id" in history.columns:
        subset = history[history["event_id"].astype(str) == str(event_id)].copy()
        if "action_timestamp" in subset.columns:
            subset = subset.sort_values("action_timestamp")
        for payload in _records(subset):
            model = _safe_model(Intervention, payload)
            if model:
                previous.append(model)

    return EventContext(
        event=event,
        customer=customer,
        subscription=subscription,
        related_transaction=related_transaction,
        recent_transactions=recent,
        previous_interventions=previous,
        metadata={"optional_joins_missing": customer is None},
    )
