import pytest

from app.core.risk_config import RiskEngineConfig
from app.services.risk.engine import (
    RiskEngineError,
    assess_revenue_risk,
    expected_recovery_value,
    rank_opportunities,
)
from tests.helpers import make_context, make_predictions


def _assess(
    amount: float = 10_000,
    recovery: float = 0.7,
    churn: float = 0.2,
    ltv: float | None = 80_000,
    urgency: str | None = "high",
    include_customer: bool = True,
    event_id: str = "EVT_TEST",
    config: RiskEngineConfig | None = None,
):
    context = make_context(
        event_id=event_id,
        amount=amount,
        urgency=urgency,
        ltv=ltv,
        include_customer=include_customer,
    )
    rec, ch = make_predictions(recovery, churn)
    return assess_revenue_risk(context, rec, ch, config=config)


def test_expected_recovery_value_is_deterministic() -> None:
    assert expected_recovery_value(10_000, 0.7) == 7000
    assert expected_recovery_value(10_000, 0.0) == 0
    assert expected_recovery_value(10_000, 1.0) == 10_000
    assert expected_recovery_value(0, 0.9) == 0


def test_priority_score_and_category_thresholds() -> None:
    high_value = _assess(amount=50_000, recovery=0.85, churn=0.7, ltv=180_000, urgency="high")
    assert high_value.expected_recovery_value == pytest.approx(42_500)
    assert high_value.priority_category == "CRITICAL"
    assert high_value.priority_score >= 70

    modest = _assess(amount=800, recovery=0.3, churn=0.05, ltv=5_000, urgency="low")
    assert modest.priority_category == "LOW"
    assert modest.priority_score < 30


def test_normalization_caps_large_amounts() -> None:
    huge = _assess(amount=10_000_000, recovery=1.0, churn=0.0, ltv=0, urgency="low")
    assert huge.component_scores.expected_recovery == 1.0
    assert huge.priority_score <= 100


def test_missing_customer_value_and_urgency() -> None:
    result = _assess(include_customer=False, urgency=None, recovery=0.5, churn=0.5, amount=5_000)
    assert result.customer_ltv is None
    assert result.component_scores.customer_value == 0.0
    assert result.urgency == "unknown"
    assert any("lifetime value is unavailable" in factor for factor in result.contributing_factors)
    assert any("Urgency was missing" in factor for factor in result.contributing_factors)


def test_contributing_factors_reflect_actual_signals() -> None:
    result = _assess(amount=40_000, recovery=0.8, churn=0.75, ltv=160_000, urgency="high")
    text = " ".join(result.contributing_factors)
    assert "expected recoverable revenue" in text.lower() or "High expected recoverable" in text
    assert "churn" in text.lower()
    assert "lifetime value" in text.lower()
    assert str(int(result.expected_recovery_value))[:2] in text or "₹" in text


def test_ranking_uses_business_value_and_is_deterministic() -> None:
    a = _assess(event_id="EVT_A", amount=1_000, recovery=0.2, churn=0.1, ltv=1_000, urgency="low")
    b = _assess(event_id="EVT_B", amount=25_000, recovery=0.8, churn=0.6, ltv=150_000, urgency="high")
    c = _assess(event_id="EVT_C", amount=25_000, recovery=0.8, churn=0.6, ltv=150_000, urgency="high")
    ranked = rank_opportunities([a, c, b])
    assert ranked[0].event_id in {"EVT_B", "EVT_C"}
    assert ranked[-1].event_id == "EVT_A"
    # Identical B/C scores: event_id breaks the tie.
    tied = [item for item in ranked if item.event_id in {"EVT_B", "EVT_C"}]
    assert [item.event_id for item in tied] == ["EVT_B", "EVT_C"]
    again = rank_opportunities([c, b, a])
    assert [item.event_id for item in again] == [item.event_id for item in ranked]


def test_same_inputs_same_category() -> None:
    first = _assess(amount=12_000, recovery=0.66, churn=0.41, ltv=90_000, urgency="medium")
    second = _assess(amount=12_000, recovery=0.66, churn=0.41, ltv=90_000, urgency="medium")
    assert first.priority_score == second.priority_score
    assert first.priority_category == second.priority_category
    assert first.expected_recovery_value == second.expected_recovery_value


def test_edge_probabilities_and_zero_amount() -> None:
    zero_amount = _assess(amount=0, recovery=1.0, churn=1.0, ltv=0, urgency="low")
    assert zero_amount.expected_recovery_value == 0
    assert zero_amount.priority_category in {"LOW", "MEDIUM"}

    no_recovery = _assess(amount=20_000, recovery=0.0, churn=0.0, ltv=0, urgency="low")
    assert no_recovery.expected_recovery_value == 0

    sure_recovery = _assess(amount=2_000, recovery=1.0, churn=0.0)
    assert sure_recovery.expected_recovery_value == 2_000

    max_churn = _assess(amount=2_000, recovery=0.4, churn=1.0, ltv=50_000)
    min_churn = _assess(amount=2_000, recovery=0.4, churn=0.0, ltv=50_000)
    assert max_churn.priority_score > min_churn.priority_score


def test_invalid_probabilities_and_negative_amount() -> None:
    with pytest.raises(RiskEngineError, match="amount_at_risk"):
        _assess(amount=-10)
    rec, ch = make_predictions(0.5, 0.2)
    invalid_recovery = rec.model_construct(
        probability=1.2,
        recoverability="medium",
        model_type="test",
        model_version="test",
    )
    context = make_context(amount=1000)
    with pytest.raises(RiskEngineError, match="recovery_probability"):
        assess_revenue_risk(context, invalid_recovery, ch)
    invalid_churn = ch.model_construct(
        probability=-0.2,
        risk_category="medium",
        model_type="test",
        model_version="test",
    )
    valid_rec, _ = make_predictions(0.5, 0.2)
    with pytest.raises(RiskEngineError, match="churn_probability"):
        assess_revenue_risk(context, valid_rec, invalid_churn)


def test_repeated_events_rank_by_id() -> None:
    first = _assess(event_id="EVT_100", amount=8_000, recovery=0.5, churn=0.3)
    duplicate = _assess(event_id="EVT_100", amount=8_000, recovery=0.5, churn=0.3)
    ranked = rank_opportunities([first, duplicate])
    assert len(ranked) == 2
    assert ranked[0].priority_score == ranked[1].priority_score


def test_custom_thresholds_are_honored() -> None:
    config = RiskEngineConfig(
        threshold_critical=90,
        threshold_high=80,
        threshold_medium=10,
    )
    result = _assess(amount=30_000, recovery=0.8, churn=0.5, ltv=100_000, urgency="high", config=config)
    assert result.priority_score < 90
    assert result.priority_category in {"HIGH", "MEDIUM"}
