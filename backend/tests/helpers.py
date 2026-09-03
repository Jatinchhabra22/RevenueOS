from datetime import datetime

from app.schemas.entities import Customer, EventContext, RevenueEvent
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction


def make_context(
    *,
    event_id: str = "EVT_TEST",
    customer_id: str = "CUS_TEST",
    amount: float = 10_000,
    urgency: str | None = "high",
    ltv: float | None = 80_000,
    include_customer: bool = True,
    failure_reason: str | None = "network_error",
    event_status: str = "open",
    previous_interventions: list | None = None,
    attempt_number: int = 1,
    payment_method: str | None = "card",
) -> EventContext:
    event = RevenueEvent(
        event_id=event_id,
        event_timestamp=datetime(2026, 8, 21, 9, 20, 0),
        merchant_id="MERCHANT_001",
        customer_id=customer_id,
        event_type="payment_failed",
        amount_at_risk=amount,
        failure_reason=failure_reason,
        attempt_number=attempt_number,
        payment_method=payment_method,
        urgency=urgency,
        event_status=event_status,
    )
    customer = None
    if include_customer:
        customer = Customer(
            customer_id=customer_id,
            merchant_id="MERCHANT_001",
            customer_ltv=ltv,
            tenure_days=400,
            payment_success_rate=0.9,
        )
    return EventContext(
        event=event,
        customer=customer,
        previous_interventions=previous_interventions or [],
    )


def make_predictions(recovery: float, churn: float) -> tuple[RecoveryPrediction, ChurnPrediction]:
    return (
        RecoveryPrediction(
            probability=recovery,
            recoverability="medium",
            model_type="test",
            model_version="test",
        ),
        ChurnPrediction(
            probability=churn,
            risk_category="medium",
            model_type="test",
            model_version="test",
        ),
    )
