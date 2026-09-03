"""Explicit, inspectable column alias maps for merchant uploads."""

from __future__ import annotations

COLUMN_ALIASES: dict[str, dict[str, str]] = {
    "customers": {
        "user_id": "customer_id",
        "customer": "customer_id",
        "cust_id": "customer_id",
        "merchant": "merchant_id",
        "segment": "customer_segment",
        "ltv": "customer_ltv",
        "lifetime_value": "customer_ltv",
    },
    "transactions": {
        "txn_id": "transaction_id",
        "transactionid": "transaction_id",
        "user_id": "customer_id",
        "customer": "customer_id",
        "status": "transaction_status",
        "txn_status": "transaction_status",
        "payment_amount": "amount",
        "transaction_value": "amount",
        "order_value": "amount",
        "failure": "failure_reason",
        "timestamp": "transaction_timestamp",
        "txn_time": "transaction_timestamp",
    },
    "subscriptions": {
        "sub_id": "subscription_id",
        "user_id": "customer_id",
        "plan_amount": "recurring_amount",
        "frequency": "billing_frequency",
        "status": "subscription_status",
        "start_date": "subscription_start_date",
    },
    "revenue_events": {
        "id": "event_id",
        "user_id": "customer_id",
        "customer": "customer_id",
        "amount": "amount_at_risk",
        "payment_amount": "amount_at_risk",
        "transaction_value": "amount_at_risk",
        "order_value": "amount_at_risk",
        "txn_id": "transaction_id",
        "failure": "failure_reason",
        "timestamp": "event_timestamp",
        "event_time": "event_timestamp",
        "status": "event_status",
        "type": "event_type",
    },
    "intervention_history": {
        "id": "intervention_id",
        "user_id": "customer_id",
        "action": "action_type",
        "timestamp": "action_timestamp",
        "result": "outcome",
        "recovered_amount": "amount_recovered",
    },
}

TABLE_ALIASES: dict[str, str] = {
    "customers": "customers",
    "customer": "customers",
    "users": "customers",
    "transactions": "transactions",
    "transaction": "transactions",
    "payments": "transactions",
    "subscriptions": "subscriptions",
    "subscription": "subscriptions",
    "revenue_events": "revenue_events",
    "events": "revenue_events",
    "revenueevents": "revenue_events",
    "intervention_history": "intervention_history",
    "interventions": "intervention_history",
    "actions": "intervention_history",
}


def canonical_table_name(filename: str) -> str | None:
    stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower().strip()
    stem = stem.replace("-", "_").replace(" ", "_")
    return TABLE_ALIASES.get(stem)


def apply_column_aliases(table: str, columns: list[str]) -> tuple[list[str], dict[str, str]]:
    mapping = COLUMN_ALIASES.get(table, {})
    applied: dict[str, str] = {}
    renamed: list[str] = []
    for column in columns:
        key = column.strip().lower()
        canonical = mapping.get(key, key if key == column.strip().lower() else column)
        # Prefer explicit alias; otherwise keep original name
        if key in mapping:
            applied[column] = mapping[key]
            renamed.append(mapping[key])
        else:
            renamed.append(column.strip())
    return renamed, applied
