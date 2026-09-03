from datetime import datetime, timedelta, timezone

from app.agents.graph import run_recovery_agent
from app.core.agent_policy import AgentPolicy
from app.core.risk_config import RiskEngineConfig
from app.schemas.entities import Intervention
from app.services.recoverability import classify_recoverability
from app.services.risk.engine import assess_revenue_risk
from tests.helpers import make_context, make_predictions


def _classify(context, recovery_p=0.6, churn_p=0.2, **kwargs):
    rec, ch = make_predictions(recovery_p, churn_p)
    risk = assess_revenue_risk(context, rec, ch)
    return classify_recoverability(context, rec, ch, risk, **kwargs)


def test_recoverable_event() -> None:
    result = _classify(make_context(amount=10_000), recovery_p=0.7)
    assert result.classification == "RECOVERABLE"
    assert result.pursue is True
    assert "worth pursuing" in result.statement.lower()


def test_low_recoverability_still_pursued_when_erv_high() -> None:
    result = _classify(make_context(amount=20_000), recovery_p=0.28)
    assert result.classification == "LOW_RECOVERABILITY"
    assert result.pursue is True


def test_low_recoverability_no_action_when_erv_low() -> None:
    result = _classify(make_context(amount=200), recovery_p=0.3)
    assert result.classification == "LOW_RECOVERABILITY"
    assert result.pursue is False
    assert "EXPECTED_VALUE_TOO_LOW" in result.reason_codes


def test_not_recoverable_event() -> None:
    result = _classify(make_context(amount=150, attempt_number=3), recovery_p=0.1)
    assert result.classification == "NOT_RECOVERABLE"
    assert result.pursue is False


def test_already_resolved_event() -> None:
    result = _classify(make_context(event_status="recovered"), recovery_p=0.9)
    assert result.classification == "ALREADY_RESOLVED"
    assert result.pursue is False


def test_action_blocked_max_attempts() -> None:
    now = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    history = [
        Intervention(
            intervention_id=f"INT_{index}",
            event_id="EVT_TEST",
            customer_id="CUS_TEST",
            action_type="send_email",
            action_timestamp=now - timedelta(days=index + 2),
            attempt_number=index,
            outcome="failed",
        )
        for index in range(1, 4)
    ]
    result = _classify(
        make_context(previous_interventions=history),
        recovery_p=0.7,
        policy=AgentPolicy(max_interventions_per_event=3, cooldown_hours=0),
    )
    assert result.classification == "ACTION_BLOCKED"
    assert result.pursue is False
    assert "MAXIMUM_ATTEMPTS_REACHED" in result.reason_codes


def test_needs_review_missing_context() -> None:
    result = _classify(make_context(include_customer=False, failure_reason=None), recovery_p=0.5)
    assert result.classification == "NEEDS_REVIEW"
    assert result.pursue is False


def test_agent_no_action_when_not_worth_pursuing() -> None:
    context = make_context(amount=80, failure_reason="bank_declined")
    rec, ch = make_predictions(0.08, 0.2)
    result = run_recovery_agent(
        context=context,
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert result["selected_action"]["action_type"] == "stop_recovery"
    assert result["outcome"]["outcome"] == "NO_ACTION"
    assert result["recoverability"]["pursue"] is False
    assert result["tool_result"]["action_type"] == "stop_recovery"


def test_agent_still_acts_on_recoverable_event() -> None:
    context = make_context(failure_reason="network_error", amount=10_000)
    rec, ch = make_predictions(0.7, 0.2)
    result = run_recovery_agent(
        context=context,
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert result["selected_action"]["action_type"] != "stop_recovery"
    assert result["recoverability"]["classification"] == "RECOVERABLE"
    assert result["outcome"]["outcome"] != "NO_ACTION"


def test_thresholds_come_from_risk_config() -> None:
    config = RiskEngineConfig(pursue_min_erv=5_000, low_recoverability_probability=0.9)
    result = _classify(make_context(amount=1_000), recovery_p=0.8, config=config)
    assert result.pursue is False
    assert result.classification in {"LOW_RECOVERABILITY", "NOT_RECOVERABLE"}
