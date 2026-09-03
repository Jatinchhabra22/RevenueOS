"""Churn features: same functions for training rows and EventContext inference."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from app.schemas.entities import EventContext, Transaction
from app.services.features.constants import CHURN_FEATURE_COLUMNS
from app.services.features.feature_utils import (
    as_datetime,
    days_between,
    normalize_category,
    ordered_frame,
    to_float,
)


def _recent_failures(transactions: Iterable[Transaction], as_of: datetime | None, window_days: int = 45) -> float:
    count = 0
    for txn in transactions:
        if str(txn.transaction_status).lower() != "failed":
            continue
        ts = as_datetime(txn.transaction_timestamp)
        if as_of is not None and ts is not None:
            age = (as_of - ts).total_seconds() / 86400.0
            if age < 0 or age > window_days:
                continue
        count += 1
    return float(count)


def churn_feature_dict(
    *,
    tenure_days: Any,
    total_spend: Any,
    customer_ltv: Any,
    engagement_score: Any,
    payment_success_rate: Any,
    previous_failures: Any,
    previous_recoveries: Any,
    failed_cycles: Any,
    avg_order_value: Any,
    total_orders: Any,
    activity_trend: Any,
    customer_segment: Any,
    has_subscription: Any,
    last_activity: Any,
    as_of: Any,
    recent_payment_failures: Any,
) -> dict[str, Any]:
    return {
        "tenure_days": to_float(tenure_days),
        "total_spend": to_float(total_spend),
        "customer_ltv": to_float(customer_ltv),
        "engagement_score": to_float(engagement_score),
        "payment_success_rate": to_float(payment_success_rate),
        "previous_failures": to_float(previous_failures, default=0.0),
        "previous_recoveries": to_float(previous_recoveries, default=0.0),
        "failed_cycles": to_float(failed_cycles, default=0.0),
        "recent_payment_failures": to_float(recent_payment_failures, default=0.0),
        "days_since_last_activity": days_between(as_datetime(as_of), as_datetime(last_activity)),
        "avg_order_value": to_float(avg_order_value),
        "total_orders": to_float(total_orders),
        "activity_trend": normalize_category(activity_trend),
        "customer_segment": normalize_category(customer_segment),
        "has_subscription": "yes" if bool(has_subscription) else "no",
    }


def churn_features_from_context(context: EventContext, as_of: datetime | None = None) -> dict[str, Any]:
    customer = context.customer
    subscription = context.subscription
    reference = as_of or context.event.event_timestamp
    recent_failures = _recent_failures(context.recent_transactions, as_datetime(reference))
    return churn_feature_dict(
        tenure_days=customer.tenure_days if customer else None,
        total_spend=customer.total_spend if customer else None,
        customer_ltv=customer.customer_ltv if customer else None,
        engagement_score=customer.engagement_score if customer else None,
        payment_success_rate=customer.payment_success_rate if customer else None,
        previous_failures=customer.previous_failures if customer else 0,
        previous_recoveries=customer.previous_recoveries if customer else 0,
        failed_cycles=subscription.failed_cycles if subscription else 0,
        avg_order_value=customer.avg_order_value if customer else None,
        total_orders=customer.total_orders if customer else None,
        activity_trend=customer.activity_trend if customer else None,
        customer_segment=customer.customer_segment if customer else None,
        has_subscription=subscription is not None,
        last_activity=customer.last_activity_date if customer else None,
        as_of=reference,
        recent_payment_failures=recent_failures,
    )


def churn_feature_frame(rows: list[dict[str, Any]]):
    return ordered_frame(rows, CHURN_FEATURE_COLUMNS)
