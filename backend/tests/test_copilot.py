from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.agents.llm.ollama_provider import OllamaLLM
from app.agents.llm.structured import LLMError
from app.api.deps import get_runtime
from app.core.config import get_settings
from app.main import app
from app.schemas.agent import (
    ActionDecision,
    AuditEntry,
    CandidateAction,
    Diagnosis,
    GuardrailResult,
    RecoveryOutcome,
    RecoveryStrategy,
    ToolResult,
)
from app.schemas.api import AgentWorkflowResponse, CopilotAskResponse
from app.services.agent_runs import persist_workflow
from app.services.copilot import ask_copilot, build_copilot_context
from app.services.data.synthetic import GeneratorConfig, generate_tables
from app.services.events import get_event_detail
from app.services.runtime import AppRuntime


class FakeLLM:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls = 0
        self.model = "llama3.2:3b"

    def generate_structured(self, **kwargs):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        return dict(self.payload)


def _write_csv(directory: Path, tables: dict[str, pd.DataFrame]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(directory / f"{name}.csv", index=False)


@pytest.fixture
def runtime(tmp_path: Path) -> AppRuntime:
    tables = generate_tables(GeneratorConfig(seed=11, n_customers=40))
    active = tmp_path / "data" / "demo"
    _write_csv(active, tables)
    settings = get_settings()
    return AppRuntime(
        data_dir=tmp_path / "data",
        artifacts_dir=settings.artifacts_path,
        models_dir=settings.models_path,
        uploads_dir=tmp_path / "data" / "uploads",
        workflows_dir=tmp_path / "artifacts" / "workflows",
        active_dataset_dir=active,
        upload_max_bytes=2_000_000,
        disable_llm=True,
    )


@pytest.fixture
def api_client(runtime: AppRuntime) -> TestClient:
    app.dependency_overrides[get_runtime] = lambda: runtime
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


def _event_ids(runtime: AppRuntime) -> list[str]:
    events = runtime.tables()["revenue_events"]
    return [str(value) for value in events["event_id"].tolist()]


def _stub_workflow(
    detail,
    *,
    strategy: RecoveryStrategy | None = RecoveryStrategy(
        recommended_action="payment_method_update",
        alternative_action="retry_now",
        reasoning_summary="Expired instrument; retrying the same card is unlikely to succeed.",
    ),
    include_execution: bool = True,
    include_audit: bool = True,
    include_strategy: bool = True,
    include_outcome: bool = True,
) -> AgentWorkflowResponse:
    action = CandidateAction(
        action_id=f"{detail.event.event_id}-ACT-01",
        action_type="payment_method_update",
        eligibility=True,
        expected_effect="replace expired instrument",
        rationale="Card expiry matches the failure reason.",
    )
    now = datetime.now(timezone.utc)
    execution = None
    if include_execution:
        execution = ToolResult(
            action_id=action.action_id,
            action_type=action.action_type,
            execution_id="EX_TEST",
            status="completed",
            timestamp=now,
            message="Simulated payment method update was recorded.",
        )
    audit: list[AuditEntry] = []
    if include_audit:
        audit = [
            AuditEntry(timestamp=now, stage="diagnose_event", decision="diagnosed", reason="expired card"),
            AuditEntry(timestamp=now, stage="select_action", decision="payment_method_update", reason="eligible"),
            AuditEntry(timestamp=now, stage="validate_guardrails", decision="ALLOW", reason="ok"),
        ]
    return AgentWorkflowResponse(
        workflow_id="WF_COPILOT_TEST",
        event_id=detail.event.event_id,
        diagnosis=Diagnosis(
            primary_issue="expired payment method",
            recoverability_reason="customer is still engaged",
            churn_concern="moderate",
            customer_context="known payer",
            recommended_strategy="payment_method_update",
            issue_category="expired_payment_method",
            event_summary="card expired",
        ),
        recovery_prediction=detail.recovery_prediction,
        churn_prediction=detail.churn_prediction,
        risk_assessment=detail.risk_assessment,
        candidate_actions=[action],
        selected_action=action,
        decision=ActionDecision(
            selected_action_id=action.action_id,
            selected_action_type=action.action_type,
            reason="Failure is tied to an expired card.",
            confidence=0.72,
            alternative_considered="retry_now",
            source="fallback",
        ),
        guardrail_result=GuardrailResult(allowed=True, status="ALLOW", reason="Policy checks passed.", reason_codes=[]),
        execution_result=execution,
        outcome=(
            RecoveryOutcome(
                outcome="PENDING",
                action_type=action.action_type,
                execution_status="completed",
                amount_recovered=0.0,
                remaining_amount_at_risk=detail.event.amount_at_risk,
                customer_impact="low",
                timestamp=now,
                explanation="Waiting for the customer to update the instrument.",
            )
            if include_outcome
            else None
        ),
        final_decision="completed",
        status="completed",
        audit_trail=audit,
        strategy=strategy if include_strategy else None,
    )


def test_copilot_valid_question_fallback(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    response = api_client.post(
        "/api/v1/copilot/ask",
        json={"event_id": event_id, "question": "Why was this action selected?"},
    )
    assert response.status_code == 200
    body = response.json()
    CopilotAskResponse.model_validate(body)
    assert body["event_id"] == event_id
    assert body["question"] == "Why was this action selected?"
    assert event_id in body["answer"]
    assert body["fallback_used"] is True
    assert body["provider"] is None
    assert "event_context" in body["sources"]
    assert "ml_predictions" in body["sources"]
    assert "risk_assessment" in body["sources"]
    assert "does not execute" in body["answer"].lower() or "read-only" in body["answer"].lower()


def test_copilot_different_event_ids(api_client: TestClient, runtime: AppRuntime) -> None:
    first, second = _event_ids(runtime)[:2]
    a = api_client.post(
        "/api/v1/copilot/ask",
        json={"event_id": first, "question": "How much revenue was at risk?"},
    ).json()
    b = api_client.post(
        "/api/v1/copilot/ask",
        json={"event_id": second, "question": "How much revenue was at risk?"},
    ).json()
    assert a["event_id"] == first
    assert b["event_id"] == second
    assert first in a["answer"]
    assert second in b["answer"]
    assert first not in b["answer"]
    assert second not in a["answer"]


def test_copilot_unknown_event(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/copilot/ask",
        json={"event_id": "EVT_DOES_NOT_EXIST", "question": "Why is this event high risk?"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EVENT_NOT_FOUND"
    assert "traceback" not in response.text.lower()


def test_copilot_empty_question(api_client: TestClient, runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    response = api_client.post("/api/v1/copilot/ask", json={"event_id": event_id, "question": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_copilot_invalid_request(api_client: TestClient) -> None:
    missing = api_client.post("/api/v1/copilot/ask", json={"event_id": "EVT_1"})
    assert missing.status_code == 422
    too_long = api_client.post(
        "/api/v1/copilot/ask",
        json={"event_id": "EVT_1", "question": "x" * 801},
    )
    assert too_long.status_code == 422
    not_json = api_client.post("/api/v1/copilot/ask", content="not-json", headers={"Content-Type": "application/json"})
    assert not_json.status_code == 422
    assert "error" in not_json.json()


def test_copilot_llm_success(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    llm = FakeLLM({"answer": f"{event_id} was explained from grounded context."})
    result = ask_copilot(
        runtime,
        event_id=event_id,
        question="Why was payment_method_update selected?",
        llm=llm,
    )
    assert llm.calls == 1
    assert result.fallback_used is False
    assert result.provider == "injected"
    assert result.model == "llama3.2:3b"
    assert result.answer.startswith(event_id)


def test_copilot_ollama_unavailable_uses_fallback(runtime: AppRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    event_id = _event_ids(runtime)[0]
    runtime.disable_llm = False
    bound = OllamaLLM(base_url="http://127.0.0.1:9", model="llama3.2:3b", timeout=1, max_retries=0)

    def boom(**kwargs):
        raise AssertionError("Ollama generate should not run when the model is unavailable")

    monkeypatch.setattr("app.services.copilot.get_llm", lambda: bound)
    monkeypatch.setattr("app.agents.llm.runtime.ollama_available", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.agents.llm.runtime.ollama_has_model", lambda *args, **kwargs: False)
    monkeypatch.setattr(bound, "generate_structured", boom)
    result = ask_copilot(runtime, event_id=event_id, question="Why is this event high risk?")
    assert result.fallback_used is True
    assert result.provider == "ollama"
    assert result.model == "llama3.2:3b"
    assert event_id in result.answer


def test_copilot_deterministic_fallback_without_llm(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    result = ask_copilot(runtime, event_id=event_id, question="What caused this payment failure?", llm=None)
    assert result.fallback_used is True
    assert result.provider is None
    assert result.model is None
    assert event_id in result.answer


def test_copilot_malformed_llm_response(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    llm = FakeLLM({"not_an_answer": True})
    result = ask_copilot(runtime, event_id=event_id, question="What should happen next?", llm=llm)
    assert llm.calls == 1
    assert result.fallback_used is True
    assert event_id in result.answer


def test_copilot_llm_timeout(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    llm = FakeLLM(LLMError("timeout"))
    result = ask_copilot(runtime, event_id=event_id, question="What happened during execution?", llm=llm)
    assert result.fallback_used is True
    assert "read-only" in result.answer.lower()


def test_copilot_llm_exception(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    llm = FakeLLM(RuntimeError("provider crashed"))
    result = ask_copilot(runtime, event_id=event_id, question="Which guardrails were checked?", llm=llm)
    assert result.fallback_used is True


def test_copilot_missing_optional_fields(runtime: AppRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    event_id = _event_ids(runtime)[0]
    detail = get_event_detail(runtime, event_id)
    slim = detail.model_copy(
        update={
            "customer": None,
            "subscription": None,
            "related_transaction": None,
            "recent_transactions": [],
            "previous_interventions": [],
        }
    )
    monkeypatch.setattr("app.services.copilot.get_event_detail", lambda *_args, **_kwargs: slim)
    context, sources = build_copilot_context(runtime, event_id)
    assert "customer_context" not in context
    assert "customer_context" not in sources
    result = ask_copilot(runtime, event_id=event_id, question="What customer context influenced the decision?")
    assert "not available in the current workflow context" in result.answer.lower()


def test_copilot_missing_audit_strategy_execution(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    detail = get_event_detail(runtime, event_id)
    persist_workflow(
        runtime,
        _stub_workflow(
            detail,
            include_execution=False,
            include_audit=False,
            include_strategy=False,
            include_outcome=False,
        ),
    )
    context, sources = build_copilot_context(runtime, event_id)
    packed = context["workflow"]
    assert packed.get("strategy") is None
    assert packed.get("execution_status") is None
    assert packed.get("audit_trail") == []
    assert "audit_trail" not in sources
    assert "execution" not in sources
    selected = ask_copilot(runtime, event_id=event_id, question="Why was this action selected?")
    assert packed["selected_action"] in selected.answer
    blocked = ask_copilot(runtime, event_id=event_id, question="What happened during execution?")
    assert "no execution result is stored" in blocked.answer.lower()


def test_copilot_with_workflow_grounding(runtime: AppRuntime) -> None:
    event_id = _event_ids(runtime)[0]
    detail = get_event_detail(runtime, event_id)
    persist_workflow(runtime, _stub_workflow(detail))
    result = ask_copilot(runtime, event_id=event_id, question="Why was payment_method_update selected?")
    assert "payment_method_update" in result.answer
    assert "strategy" in result.sources
    assert "guardrails" in result.sources
    assert "execution" in result.sources
    assert "audit_trail" in result.sources


def test_copilot_context_restricted_to_event(runtime: AppRuntime) -> None:
    ids = _event_ids(runtime)
    event_id = ids[0]
    context, _sources = build_copilot_context(runtime, event_id)
    blob = str(context)
    assert event_id in blob
    for other in ids[1:12]:
        assert other not in blob


def test_copilot_does_not_run_agent_or_mutate(runtime: AppRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    event_id = _event_ids(runtime)[0]

    def boom(*args, **kwargs):
        raise AssertionError("Copilot must not execute the recovery agent")

    monkeypatch.setattr("app.services.agent_runs.run_event_agent", boom)
    monkeypatch.setattr("app.agents.graph.run_recovery_agent", boom)
    before = list((runtime.workflows_dir / event_id).glob("*")) if (runtime.workflows_dir / event_id).exists() else []
    ask_copilot(runtime, event_id=event_id, question="Why was retry_now selected?")
    after = list((runtime.workflows_dir / event_id).glob("*")) if (runtime.workflows_dir / event_id).exists() else []
    assert before == after


def test_copilot_api_llm_success(runtime: AppRuntime, monkeypatch: pytest.MonkeyPatch) -> None:
    event_id = _event_ids(runtime)[0]
    runtime.disable_llm = False
    llm = FakeLLM({"answer": f"Grounded answer for {event_id}."})
    monkeypatch.setattr("app.services.copilot.get_llm", lambda: llm)
    app.dependency_overrides[get_runtime] = lambda: runtime
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            "/api/v1/copilot/ask",
            json={"event_id": event_id, "question": "Why was this action selected?"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_used"] is False
    assert body["provider"] == "FakeLLM"
    assert body["model"] == "llama3.2:3b"
    assert llm.calls == 1
    assert event_id in body["answer"]
