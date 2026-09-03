"""Record LLM invocations without storing prompts, keys, or chain-of-thought."""

from __future__ import annotations

import time
from typing import Any

from app.agents.llm.provider import LLMError

_SCHEMA_AGENT = {
    "SupervisorDecision": "supervisor",
    "InvestigationResult": "investigator",
    "Diagnosis": "diagnosis",
    "CustomerAnalysis": "customer_analyst",
    "ActionDecision": "strategist",
    "RecoveryStrategy": "strategist",
    "ReflectionResult": "reflection",
}


class TracingLLM:
    def __init__(self, inner: Any, records: list[dict[str, Any]]) -> None:
        self.inner = inner
        self.records = records
        self.model = getattr(inner, "model", None)
        self.base_url = getattr(inner, "base_url", None)

    def generate_structured(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        started = time.perf_counter()
        agent = _SCHEMA_AGENT.get(schema_name, "llm")
        self.records.append(
            {
                "event_type": "LLM_CALL_STARTED",
                "schema_name": schema_name,
                "agent": agent,
                "model": self.model,
                "provider": "ollama" if "Ollama" in type(self.inner).__name__ else type(self.inner).__name__,
            }
        )
        try:
            payload = self.inner.generate_structured(system=system, user=user, schema_name=schema_name)
        except Exception as exc:
            self.records.append(
                {
                    "event_type": "LLM_CALL_COMPLETED",
                    "schema_name": schema_name,
                    "agent": agent,
                    "model": self.model,
                    "provider": "ollama" if "Ollama" in type(self.inner).__name__ else type(self.inner).__name__,
                    "success": False,
                    "error": type(exc).__name__,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }
            )
            if isinstance(exc, LLMError):
                raise
            raise LLMError("LLM request failed") from exc
        self.records.append(
            {
                "event_type": "LLM_CALL_COMPLETED",
                "schema_name": schema_name,
                "agent": agent,
                "model": self.model,
                "provider": "ollama" if "Ollama" in type(self.inner).__name__ else type(self.inner).__name__,
                "success": True,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )
        return payload
