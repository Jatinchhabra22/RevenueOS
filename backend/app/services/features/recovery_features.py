"""Recovery features: same functions for training rows and EventContext inference."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from app.schemas.entities import EventContext, Transaction
from app.services.features.constants import RECOVERY_FEATURE_COLUMNS
from app.services.features.feature_utils import (
    as_datetime,
    days_between,
    normalize_category,
    ordered_frame,
    to_float,
    to_int,
)


def _txn_stats(transactions: Iterable[Transaction], as_of: datetime | None) -> dict[str, float | None]:
    eligible: list[Transaction] = []
    for txn in transactions:
        ts = as_datetime(txn.transaction_timestamp)
        if as_of is not None and ts is not None and ts > as_of:
            continue
        eligible.append(txn)

    count = len(eligible)
    failed = sum(1 for txn in eligible if str(txn.transaction_status).lower() == "failed")
    success = sum(1 for txn in eligible if str(txn.transaction_status).lower() == "success")
    last_ts = None
    for txn in eligible:
        ts = as_datetime(txn.transaction_timestamp)
        if ts is not None and (last_ts is None or ts > last_ts):
            last_ts = ts
    return {
        "recent_transaction_count": float(count),
        "recent_failure_rate": (failed / count) if count else None,
        "payment_success_rate": (success / count) if count else None,
        "previous_failures": float(failed),
        "last_activity": last_ts,
    }


def recovery_feature_dict(
    *,
    amount_at_risk: Any,
    attempt_number: Any,
    failure_reason: Any,
    payment_method: Any,
    event_type: Any,
    urgency: Any,
    event_timestamp: Any,
    is_recurring: Any,
    tenure_days: Any,
    engagement_score: Any,
    activity_trend: Any,
    customer_segment: Any,
    previous_recoveries: Any,
    failed_cycles: Any,
    transactions: Iterable[Transaction] = (),
    fallback_payment_success_rate: Any = None,
    fallback_previous_failures: Any = None,
    fallback_last_activity: Any = None,
) -> dict[str, Any]:
    as_of = as_datetime(event_timestamp)
    stats = _txn_stats(transactions, as_of)
    recoveries = to_float(previous_recoveries, default=0.0) or 0.0
    failures = stats["previous_failures"]
    if failures is None:
        failures = to_float(fallback_previous_failures, default=0.0) or 0.0
    success_rate = stats["payment_success_rate"]
    if success_rate is None:
        success_rate = to_float(fallback_payment_success_rate)
    last_activity = stats["last_activity"] or as_datetime(fallback_last_activity)
    historical_recovery_rate = recoveries / (recoveries + failures) if (recoveries + failures) > 0 else None

    return {
        "amount_at_risk": to_float(amount_at_risk),
        "attempt_number": to_float(attempt_number, default=1.0),
        "payment_success_rate": success_rate,
        "previous_failures": failures,
        "previous_recoveries": recoveries,
        "customer_tenure": to_float(tenure_days),
        "engagement_score": to_float(engagement_score),
        "days_since_last_activity": days_between(as_of, last_activity),
        "is_recurring": 1.0 if bool(is_recurring) else 0.0,
        "recent_failure_rate": stats["recent_failure_rate"],
        "historical_recovery_rate": historical_recovery_rate,
        "failed_cycles": to_float(failed_cycles, default=0.0),
        "recent_transaction_count": stats["recent_transaction_count"],
        "failure_reason": normalize_category(failure_reason),
        "payment_method": normalize_category(payment_method),
        "event_type": normalize_category(event_type),
        "activity_trend": normalize_category(activity_trend),
        "urgency": normalize_category(urgency),
        "customer_segment": normalize_category(customer_segment),
    }


def recovery_features_from_context(context: EventContext) -> dict[str, Any]:
    customer = context.customer
    subscription = context.subscription
    event = context.event
    current_recovered = any(item.outcome == "recovered" for item in context.previous_interventions)
    previous_recoveries = to_int(customer.previous_recoveries, default=0) if customer else 0
    if current_recovered and previous_recoveries:
        previous_recoveries = max(previous_recoveries - 1, 0)
    is_recurring = bool(event.subscription_id) or bool(
        context.related_transaction.is_recurring if context.related_transaction else False
    )
    return recovery_feature_dict(
        amount_at_risk=event.amount_at_risk,
        attempt_number=event.attempt_number,
        failure_reason=event.failure_reason,
        payment_method=event.payment_method,
        event_type=event.event_type,
        urgency=event.urgency,
        event_timestamp=event.event_timestamp,
        is_recurring=is_recurring,
        tenure_days=customer.tenure_days if customer else None,
        engagement_score=customer.engagement_score if customer else None,
        activity_trend=customer.activity_trend if customer else None,
        customer_segment=customer.customer_segment if customer else None,
        previous_recoveries=previous_recoveries,
        failed_cycles=subscription.failed_cycles if subscription else 0,
        transactions=context.recent_transactions,
        fallback_payment_success_rate=customer.payment_success_rate if customer else None,
        fallback_previous_failures=customer.previous_failures if customer else None,
        fallback_last_activity=customer.last_activity_date if customer else None,
    )


def recovery_feature_frame(rows: list[dict[str, Any]]):
    return ordered_frame(rows, RECOVERY_FEATURE_COLUMNS)
