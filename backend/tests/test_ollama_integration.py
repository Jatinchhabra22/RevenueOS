"""Live Ollama checks. Skipped automatically when llama3.2:3b is not available."""

from __future__ import annotations

import pytest

from app.agents.graph import run_recovery_agent
from app.agents.llm.ollama_provider import OllamaLLM, ollama_available, ollama_has_model
from app.agents.llm.runtime import agent_health_payload, describe_runtime
from app.agents.llm.structured import invoke_structured
from app.core.config import get_settings
from app.schemas.agent import Diagnosis
from tests.helpers import make_context, make_predictions


OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"


def _ollama_ready() -> bool:
    return ollama_available(OLLAMA_URL) and ollama_has_model(OLLAMA_URL, OLLAMA_MODEL)


pytestmark = [
    pytest.mark.ollama,
    pytest.mark.skipif(not _ollama_ready(), reason="Ollama llama3.2:3b is not available"),
]


@pytest.fixture
def ollama_mode(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_URL)
    monkeypatch.setenv("OLLAMA_MODEL", OLLAMA_MODEL)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_ollama_agent_health_endpoint(ollama_mode, client) -> None:
    from app.api.deps import reset_runtime

    reset_runtime()
    core = client.get("/health")
    assert core.status_code == 200
    assert core.json()["status"] == "healthy"
    response = client.get("/api/v1/agent/health")
    assert response.status_code == 200
    body = response.json()
    assert body["configured_mode"] == "ollama"
    assert body["llm_available"] is True
    assert body["provider"] == "ollama"
    assert body["model"] == OLLAMA_MODEL
    reset_runtime()
    payload = agent_health_payload()
    assert payload["configured_mode"] == "ollama"
    assert payload["llm_available"] is True
    assert payload["provider"] == "ollama"
    assert payload["model"] == OLLAMA_MODEL
    assert payload["fallback_available"] is True
    assert payload["ollama_reachable"] is True
    assert payload["ollama_model_present"] is True


def test_ollama_structured_output(ollama_mode) -> None:
    llm = OllamaLLM(base_url=OLLAMA_URL, model=OLLAMA_MODEL, timeout=90.0, max_retries=1)
    parsed = invoke_structured(
        llm,
        schema=Diagnosis,
        system="Diagnose using only supplied facts. Return JSON for schema Diagnosis.",
        user=(
            "Return a JSON object with keys: primary_issue, recoverability_reason, "
            "churn_concern, customer_context, recommended_strategy, issue_category, "
            "event_summary, key_factors, risk_notes. Failure is card_expired. Amount 1000."
        ),
        extra={"source": "llm"},
    )
    assert parsed.source == "llm"
    assert parsed.primary_issue
    assert parsed.issue_category


def test_ollama_agent_mode_and_calls(ollama_mode) -> None:
    rec, ch = make_predictions(0.4, 0.3)
    result = run_recovery_agent(
        context=make_context(failure_reason="card_expired"),
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert result["agent_mode"] == "ollama"
    assert result["provider"] == "ollama"
    assert result["model"] == OLLAMA_MODEL
    assert result["used_llm"] is True
    assert result["fallback_used"] is False
    assert int(result.get("llm_call_count") or 0) >= 3
    schemas = {
        item.get("schema_name")
        for item in (result.get("llm_calls") or [])
        if item.get("event_type") == "LLM_CALL_COMPLETED" and item.get("success")
    }
    assert "SupervisorDecision" in schemas
    assert "Diagnosis" in schemas
    assert "CustomerAnalysis" in schemas
    assert "ActionDecision" in schemas
    assert "InvestigationResult" in schemas
    if result.get("reflection"):
        assert "ReflectionResult" in schemas
    tools = {
        item.get("tool_name")
        for item in (result.get("agent_trace") or [])
        if item.get("event_type") == "TOOL_CALL"
    }
    assert "get_event_details" in tools
    assert result["recovery_prediction"]["probability"] == 0.4
    assert result["churn_prediction"]["probability"] == 0.3
    assert result["selected_action"]["action_id"] in {item["action_id"] for item in result["candidate_actions"]}
    assert result["guardrail_result"]["status"] in {"ALLOW", "BLOCK"}


def test_ollama_invalid_action_still_guardrailed(ollama_mode) -> None:
    rec, ch = make_predictions(0.4, 0.2)
    result = run_recovery_agent(
        context=make_context(event_status="resolved", failure_reason="network_error"),
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert result["guardrail_result"]["allowed"] is False
    assert not result.get("tool_result")


def test_ollama_fallback_when_forced_off(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODE", "deterministic_fallback")
    get_settings.cache_clear()
    rec, ch = make_predictions(0.4, 0.2)
    result = run_recovery_agent(
        context=make_context(),
        llm=None,
        recovery_prediction=rec.model_dump(mode="json"),
        churn_prediction=ch.model_dump(mode="json"),
    )
    assert result["fallback_used"] is True
    assert result["agent_mode"] == "deterministic_fallback"
    assert result["used_llm"] is False
    get_settings.cache_clear()
