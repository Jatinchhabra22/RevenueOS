"""Stable feature contracts shared by training and inference."""

from __future__ import annotations

# Columns that must never enter model inputs.
LEAKAGE_COLUMNS = frozenset(
    {
        "churned",
        "outcome",
        "amount_recovered",
        "event_status",
        "target_recovered",
        "target_churned",
        "response_time_hours",
    }
)

UNKNOWN_CATEGORY = "unknown"

RECOVERY_NUMERIC_FEATURES: tuple[str, ...] = (
    "amount_at_risk",
    "attempt_number",
    "payment_success_rate",
    "previous_failures",
    "previous_recoveries",
    "customer_tenure",
    "engagement_score",
    "days_since_last_activity",
    "is_recurring",
    "recent_failure_rate",
    "historical_recovery_rate",
    "failed_cycles",
    "recent_transaction_count",
)

RECOVERY_CATEGORICAL_FEATURES: tuple[str, ...] = (
    "failure_reason",
    "payment_method",
    "event_type",
    "activity_trend",
    "urgency",
    "customer_segment",
)

RECOVERY_FEATURE_COLUMNS: tuple[str, ...] = RECOVERY_NUMERIC_FEATURES + RECOVERY_CATEGORICAL_FEATURES

CHURN_NUMERIC_FEATURES: tuple[str, ...] = (
    "tenure_days",
    "total_spend",
    "customer_ltv",
    "engagement_score",
    "payment_success_rate",
    "previous_failures",
    "previous_recoveries",
    "failed_cycles",
    "recent_payment_failures",
    "days_since_last_activity",
    "avg_order_value",
    "total_orders",
)

CHURN_CATEGORICAL_FEATURES: tuple[str, ...] = (
    "activity_trend",
    "customer_segment",
    "has_subscription",
)

CHURN_FEATURE_COLUMNS: tuple[str, ...] = CHURN_NUMERIC_FEATURES + CHURN_CATEGORICAL_FEATURES
