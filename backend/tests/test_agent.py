from datetime import datetime, timedelta, timezone

from app.agents.candidates import generate_candidate_actions
from app.agents.graph import build_recovery_graph, run_recovery_agent
from app.agents.guardrails import validate_guardrails
from app.agents.llm.fallback import fallback_select_action
from app.core.agent_policy import AgentPolicy
from app.schemas.entities import Intervention
from app.services.risk.engine import assess_revenue_risk
from tests.helpers import make_context, make_predictions


class FakeLLM:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def generate_structured(self, **kwargs) -> dict:
        self.calls += 1
        return dict(self.payload)


def _run(context, llm=None, recovery=0.7, churn=0.2):
    rec, ch = make_predictions(recovery, churn)
    return run_recovery_agent(
        context=context,
        llm=llm,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )


def test_graph_compiles() -> None:
    compiled = build_recovery_graph()
    assert compiled is not None
    assert hasattr(compiled, "invoke")


def test_happy_path_without_llm() -> None:
    result = _run(make_context(failure_reason="network_error"))
    stages = [entry["stage"] for entry in result["audit_trail"]]
    for required in (
        "assemble_context",
        "diagnose_event",
        "get_predictions",
        "assess_revenue_risk",
        "generate_candidate_actions",
        "select_action",
        "validate_guardrails",
        "execute_action",
        "monitor_result",
        "finalize",
    ):
        assert required in stages
    assert result["diagnosis"]["source"] == "fallback"
    assert result["decision"]["source"] == "fallback"
    assert result["used_llm"] is False
    assert result["guardrail_result"]["allowed"] is True
    assert result["outcome"]["outcome"] in {"RECOVERED", "NOT_RECOVERED", "PENDING", "NO_ACTION"}
    assert result["next_step"] == "END"
    assert stages.count("finalize") == 1


def test_malformed_llm_response_falls_back() -> None:
    result = _run(make_context(), llm=FakeLLM({"nonsense": True}))
    assert result["decision"]["source"] == "fallback"
    assert result["selected_action"]["action_id"] in {
        item["action_id"] for item in result["candidate_actions"]
    }


def test_invalid_selected_action_falls_back() -> None:
    result = _run(
        make_context(),
        llm=FakeLLM(
            {
                "selected_action_id": "EVT_FAKE-ACT-99",
                "reason": "invented",
                "confidence": 0.9,
            }
        ),
    )
    assert result["decision"]["source"] == "fallback"
    assert result["selected_action"]["action_id"] != "EVT_FAKE-ACT-99"


def test_valid_llm_selection_is_used() -> None:
    context = make_context(failure_reason="card_expired")
    rec, ch = make_predictions(0.4, 0.2)
    risk = assess_revenue_risk(context, rec, ch)
    candidates = generate_candidate_actions(context, churn=ch, risk=risk)
    target = next(item for item in candidates if item.action_type == "generate_payment_link")
    llm = FakeLLM(
        {
            "selected_action_id": target.action_id,
            "reason": "Provide an alternate payment path.",
            "confidence": 0.8,
        }
    )
    result = _run(context, llm=llm, recovery=0.4, churn=0.2)
    assert result["used_llm"] is True
    seen = [item.get("action_type") for item in result.get("iteration_history") or []]
    seen.append(result["selected_action"]["action_type"])
    assert target.action_type in seen
    assert result["selected_action"]["action_id"] in {
        item["action_id"] for item in result["candidate_actions"]
    }


def test_guardrail_rejects_closed_event() -> None:
    result = _run(make_context(event_status="resolved", failure_reason="network_error"))
    assert result["guardrail_result"]["allowed"] is False
    assert result["status"] == "blocked"
    assert not result.get("tool_result")


def test_duplicate_and_cooldown_enforced() -> None:
    now = datetime.now(timezone.utc)
    prior = Intervention(
        intervention_id="INT_OLD",
        event_id="EVT_TEST",
        customer_id="CUS_TEST",
        action_type="retry_now",
        action_timestamp=now - timedelta(hours=1),
        attempt_number=1,
        outcome="failed",
    )
    context = make_context(failure_reason="network_error", previous_interventions=[prior])
    candidates = generate_candidate_actions(context)
    retry = next(item for item in candidates if item.action_type == "retry_now")
    blocked = validate_guardrails(
        selected_action_id=retry.action_id,
        selected_action_type="retry_now",
        candidates=candidates,
        context=context,
        now=now,
        policy=AgentPolicy(cooldown_hours=24),
    )
    assert blocked.allowed is False
    assert any("cooldown" in item for item in blocked.violations)


def test_no_action_flow() -> None:
    context = make_context(failure_reason="network_error")
    rec, ch = make_predictions(0.5, 0.1)
    risk = assess_revenue_risk(context, rec, ch)
    candidates = generate_candidate_actions(context, churn=ch, risk=risk)
    stop = next(item for item in candidates if item.action_type == "stop_recovery")
    result = _run(
        context,
        llm=FakeLLM(
            {
                "selected_action_id": stop.action_id,
                "reason": "Stop.",
                "confidence": 0.7,
            }
        ),
        recovery=0.5,
        churn=0.1,
    )
    assert result["selected_action"]["action_type"] == "stop_recovery"
    assert result["outcome"]["outcome"] == "NO_ACTION"
    assert result["status"] == "no_action"


def test_card_expired_excludes_blind_retry() -> None:
    candidates = generate_candidate_actions(make_context(failure_reason="card_expired"))
    types = {item.action_type for item in candidates}
    assert "retry_now" not in types
    assert "payment_method_update" in types


def test_fallback_selection_stays_in_candidates() -> None:
    context = make_context(failure_reason="insufficient_funds")
    rec, ch = make_predictions(0.5, 0.8)
    candidates = generate_candidate_actions(context, churn=ch)
    decision = fallback_select_action(candidates, context, rec, ch, None)
    assert decision.selected_action_id in {item.action_id for item in candidates}


def test_audit_trail_and_execution_result() -> None:
    result = _run(make_context())
    assert result["tool_result"]["execution_id"].startswith("EXE_")
    assert "timestamp" in result["tool_result"]
    assert result["outcome"]["remaining_amount_at_risk"] >= 0
    assert len(result["audit_trail"]) >= 8


def test_missing_llm_key_uses_deterministic_fallback() -> None:
    result = _run(make_context(), llm=None)
    assert result["used_llm"] is False
    assert result["diagnosis"]["source"] == "fallback"
    assert result["decision"]["source"] == "fallback"


def test_max_interventions_block_execution() -> None:
    now = datetime.now(timezone.utc)
    history = [
        Intervention(
            intervention_id=f"INT_{i}",
            event_id="EVT_TEST",
            customer_id="CUS_TEST",
            action_type="send_email",
            action_timestamp=now - timedelta(days=i + 2),
            attempt_number=i,
            outcome="failed",
        )
        for i in range(1, 4)
    ]
    result = _run(make_context(previous_interventions=history), llm=None)
    assert result["guardrail_result"]["allowed"] is False
    assert result["status"] == "blocked"
    assert result["outcome"]["outcome"] == "BLOCKED"
    assert not result.get("tool_result")


def test_outcome_uses_recovery_probability_not_labels() -> None:
    recovered = _run(make_context(), llm=None, recovery=0.99, churn=0.1)
    failed = _run(make_context(), llm=None, recovery=0.02, churn=0.1)
    assert recovered["outcome"]["outcome"] in {"RECOVERED", "PENDING", "NOT_RECOVERED", "NO_ACTION"}
    assert failed["outcome"]["outcome"] in {"RECOVERED", "PENDING", "NOT_RECOVERED", "NO_ACTION"}
    assert "actual_outcome" not in (recovered.get("event_context") or {})


def test_simulator_source_does_not_use_ground_truth_labels() -> None:
    from inspect import getsource

    from app.tools import simulator

    source = getsource(simulator)
    assert "event_status" not in source
    assert "churned" not in source
    assert "amount_recovered" not in source

