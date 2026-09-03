from __future__ import annotations

import httpx
import pytest

from app.agents.llm.ollama_provider import OllamaLLM
from app.agents.llm.provider import HttpJsonLLM, LLMError
from app.agents.llm.runtime import agent_health_payload, bind_llm, describe_runtime
from app.agents.llm.structured import invoke_structured, parse_json_object
from app.core.config import get_settings
from app.schemas.agent import ActionDecision, InvestigationResult


class FakeLLM:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls = 0

    def generate_structured(self, **kwargs):
        self.calls += 1
        if isinstance(self.payload, Exception):
            raise self.payload
        return dict(self.payload)


def test_parse_json_object_fences_and_empty() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```')["a"] == 1
    with pytest.raises(LLMError):
        parse_json_object("")
    with pytest.raises(LLMError):
        parse_json_object("not json")
    with pytest.raises(LLMError):
        parse_json_object("[1,2]")


def test_invoke_structured_unwraps_named_envelope() -> None:
    from app.schemas.agent import Diagnosis

    parsed = invoke_structured(
        FakeLLM(
            {
                "Diagnosis": {
                    "primary_issue": "expired card",
                    "recoverability_reason": "instrument is dead",
                    "churn_concern": "low",
                    "customer_context": "known",
                    "recommended_strategy": "update method",
                    "issue_category": "expired_payment_method",
                    "event_summary": "card expired",
                    "risk_notes": "",
                }
            }
        ),
        schema=Diagnosis,
        system="s",
        user="u",
        extra={"source": "llm"},
    )
    assert parsed.primary_issue == "expired card"
    assert parsed.risk_notes == []
    assert parsed.source == "llm"

    messy = invoke_structured(
        FakeLLM(
            {
                "primary_issue": "expired card",
                "recoverability_reason": ["insufficient_funds"],
                "churn_concern": "low",
                "customer_context": {"card_age": 12},
                "recommended_strategy": ["send_notification"],
                "issue_category": "expired_payment_method",
                "event_summary": ["card_expired", "retry"],
            }
        ),
        schema=Diagnosis,
        system="s",
        user="u",
        extra={"source": "llm"},
    )
    assert "insufficient_funds" in messy.recoverability_reason
    assert "send_notification" in messy.recommended_strategy


def test_invoke_structured_validates_schema() -> None:
    parsed = invoke_structured(
        FakeLLM({"facts_found": ["x"], "evidence_summary": "ok", "confidence": 0.4}),
        schema=InvestigationResult,
        system="s",
        user="u",
    )
    assert parsed.facts_found == ["x"]
    with pytest.raises(LLMError):
        invoke_structured(
            FakeLLM({"selected_action_id": "bad"}),
            schema=ActionDecision,
            system="s",
            user="u",
            extra={"source": "llm"},
        )


def test_http_llm_malformed_and_timeout(monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(httpx, "post", timeout)
    client = HttpJsonLLM(api_key="x", model="m", base_url="http://127.0.0.1:9", max_retries=0)
    with pytest.raises(LLMError):
        client.generate_structured(system="s", user="u", schema_name="X")


def test_ollama_unavailable_raises(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    client = OllamaLLM(base_url="http://127.0.0.1:9", model="llama3.2:3b", max_retries=0)
    with pytest.raises(LLMError, match="failed"):
        client.generate_structured(system="s", user="u", schema_name="X")


def test_bind_llm_respects_deterministic_mode(monkeypatch) -> None:
    from app.core.config import Settings

    monkeypatch.setattr("app.agents.llm.runtime.get_settings", lambda: Settings(agent_mode="deterministic_fallback"))
    assert bind_llm() is None
    info = describe_runtime(None)
    assert info["agent_mode"] == "deterministic_fallback"
    assert info["fallback_used"] is True


def test_agent_health_when_ollama_forced_and_down(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODE", "ollama")
    get_settings.cache_clear()
    monkeypatch.setattr("app.agents.llm.runtime.ollama_available", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.agents.llm.runtime.ollama_has_model", lambda *args, **kwargs: False)
    payload = agent_health_payload()
    assert payload["configured_mode"] == "ollama"
    assert payload["llm_available"] is False
    assert payload["fallback_available"] is True
    assert payload["ollama_reachable"] is False
    get_settings.cache_clear()
    payload = agent_health_payload()
    assert payload["fallback_available"] is True
    assert "configured_mode" in payload
