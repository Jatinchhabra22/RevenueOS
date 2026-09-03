"""Canonical Pydantic contracts for merchant entities and event context."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Customer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    customer_id: str
    merchant_id: str
    signup_date: datetime | None = None
    customer_segment: str | None = None
    tenure_days: int | None = None
    total_orders: int | None = None
    total_spend: float | None = None
    avg_order_value: float | None = None
    payment_success_rate: float | None = None
    previous_failures: int | None = None
    previous_recoveries: int | None = None
    engagement_score: float | None = None
    activity_trend: str | None = None
    customer_ltv: float | None = None
    last_activity_date: datetime | None = None
    churned: int | None = None


class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    transaction_id: str
    customer_id: str
    merchant_id: str
    transaction_timestamp: datetime
    amount: float
    currency: str = "INR"
    payment_method: str | None = None
    transaction_status: str
    failure_reason: str | None = None
    attempt_number: int | None = None
    subscription_id: str | None = None
    is_recurring: bool | None = None


class Subscription(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subscription_id: str
    customer_id: str
    merchant_id: str
    subscription_start_date: datetime
    subscription_status: str
    recurring_amount: float
    billing_frequency: str
    successful_cycles: int | None = None
    failed_cycles: int | None = None
    next_billing_date: datetime | None = None


class RevenueEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_id: str
    event_timestamp: datetime
    merchant_id: str
    customer_id: str
    event_type: str
    amount_at_risk: float
    payment_method: str | None = None
    failure_reason: str | None = None
    attempt_number: int | None = None
    transaction_id: str | None = None
    subscription_id: str | None = None
    urgency: str | None = None
    event_status: str


class Intervention(BaseModel):
    model_config = ConfigDict(extra="ignore")

    intervention_id: str
    event_id: str
    customer_id: str
    action_type: str
    action_timestamp: datetime
    attempt_number: int
    outcome: str
    amount_recovered: float | None = None
    response_time_hours: float | None = None


class EventContext(BaseModel):
    """Joined context handed to features, ML, risk, and agents."""

    event: RevenueEvent
    customer: Customer | None = None
    subscription: Subscription | None = None
    related_transaction: Transaction | None = None
    recent_transactions: list[Transaction] = Field(default_factory=list)
    previous_interventions: list[Intervention] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


MerchantPolicy = dict[str, Any]

PriorityCategory = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
