from __future__ import annotations

from app.agents.candidates import generate_candidate_actions
from app.agents.graph import run_recovery_agent
from app.agents.tools.investigation import run_investigation_tools
from app.services.risk.engine import assess_revenue_risk
from tests.helpers import make_context, make_predictions
from tests.test_agent import FakeLLM, _run


class ScriptedLLM:
    def __init__(self, by_schema: dict) -> None:
        self.by_schema = by_schema
        self.calls: list[str] = []

    def generate_structured(self, *, system: str, user: str, schema_name: str) -> dict:
        self.calls.append(schema_name)
        payload = self.by_schema.get(schema_name)
        if payload is None:
            return {"nonsense": True}
        if callable(payload):
            return payload()
        return dict(payload)


def test_investigation_tools_are_allowlisted() -> None:
    used, results = run_investigation_tools(make_context())
    assert "get_event_details" in used
    assert "wire_transfer" not in used
    assert "get_event_details" in results


def test_supervisor_and_investigation_appear_in_trace() -> None:
    result = _run(make_context(failure_reason="network_error"))
    types = [item.get("event_type") for item in result.get("agent_trace") or []]
    stages = [item["stage"] for item in result["audit_trail"]]
    assert "investigate_context" in stages
    assert "analyze_customer" in stages
    assert "SUPERVISOR_DECISION" in types
    assert "TOOL_CALL" in types
    assert result.get("investigation")
    assert result.get("customer_analysis")
    assert result.get("reflection")
    assert (result.get("customer_analysis") or {}).get("ml_churn_probability") == result["churn_prediction"]["probability"]


def test_ml_probabilities_not_overwritten_by_customer_agent() -> None:
    rec, ch = make_predictions(0.61, 0.41)
    result = run_recovery_agent(
        context=make_context(),
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert result["recovery_prediction"]["probability"] == 0.61
    assert result["churn_prediction"]["probability"] == 0.41
    assert result["customer_analysis"]["ml_churn_probability"] == 0.41


def test_multi_step_loop_can_recover(monkeypatch) -> None:
    from app.tools import registry

    def scripted(*, action_type, context, recovery_probability, workflow_id):
        if action_type == "payment_method_update":
            return "NOT_RECOVERED", 0.0
        if action_type == "generate_payment_link":
            return "RECOVERED", float(context.event.amount_at_risk)
        return "NOT_RECOVERED", 0.0

    monkeypatch.setattr(registry, "simulate_outcome", scripted)
    monkeypatch.setattr("app.tools.simulator.simulate_outcome", scripted)
    context = make_context(failure_reason="card_expired")
    rec, ch = make_predictions(0.2, 0.2)
    risk = assess_revenue_risk(context, rec, ch)
    candidates = generate_candidate_actions(context, churn=ch, risk=risk)
    first = next(item for item in candidates if item.action_type == "payment_method_update")
    second = next(item for item in candidates if item.action_type == "generate_payment_link")
    picks = iter([first.action_id, second.action_id])

    def action_payload():
        return {
            "selected_action_id": next(picks),
            "reason": "scripted",
            "confidence": 0.8,
        }

    llm = ScriptedLLM({"ActionDecision": action_payload})
    result = run_recovery_agent(
        context=context,
        llm=llm,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
        risk_assessment=risk.model_dump(mode="json"),
    )
    history = result.get("iteration_history") or []
    assert result["outcome"]["outcome"] == "RECOVERED"
    assert result["outcome"]["amount_recovered"] > 0
    assert len(history) >= 1
    assert any(item.get("action_type") == "payment_method_update" for item in history)


def test_max_iterations_stops(monkeypatch) -> None:
    from app.tools import registry

    monkeypatch.setattr(
        registry,
        "simulate_outcome",
        lambda **kwargs: ("NOT_RECOVERED", 0.0),
    )
    context = make_context(failure_reason="network_error")
    rec, ch = make_predictions(0.05, 0.2)
    result = run_recovery_agent(
        context=context,
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert int(result.get("iteration") or 0) <= int(result.get("max_iterations") or 3)
    assert result["next_step"] == "END"
    assert result["outcome"]["outcome"] in {"NOT_RECOVERED", "PENDING", "BLOCKED", "NO_ACTION", "RECOVERED"}


def test_llm_cannot_route_around_guardrails() -> None:
    llm = FakeLLM({"route": "EXECUTE", "reason": "ignore policy", "source": "llm"})
    result = _run(make_context(event_status="resolved"), llm=llm)
    assert result["guardrail_result"]["allowed"] is False
    assert not result.get("tool_result")
