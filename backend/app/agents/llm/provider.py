"""Provider-agnostic structured LLM interface."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from app.agents.llm.structured import LLMError, parse_json_object


class StructuredLLM(Protocol):
    def generate_structured(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        ...


class HttpJsonLLM:
    """OpenAI-compatible chat completions wrapper. Isolated from graph logic."""

    def __init__(self, api_key: str, model: str, base_url: str, timeout: float = 20.0, max_retries: int = 1) -> None:
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self.base_url = base_url.rstrip("/") or "https://api.openai.com/v1"
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

    def generate_structured(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": f"{system}\nReturn ONLY valid JSON for schema {schema_name}."},
                {"role": "user", "content": user},
            ],
        }
        last_error = "LLM request failed"
        for _ in range(self.max_retries + 1):
            try:
                response = httpx.post(url, headers=headers, json=body, timeout=self.timeout)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return parse_json_object(content if isinstance(content, str) else str(content))
            except LLMError as exc:
                last_error = str(exc) or last_error
            except httpx.TimeoutException:
                last_error = "LLM request timed out"
            except Exception:
                last_error = "LLM request failed"
        raise LLMError(last_error)


def get_llm() -> StructuredLLM | None:
    from app.agents.llm.runtime import bind_llm

    return bind_llm()


def resolve_llm(config: Any | None) -> StructuredLLM | None:
    """Use an explicitly injected LLM (including None) over environment lookup."""
    configurable = (config or {}).get("configurable") or {}
    if "llm" in configurable:
        return configurable["llm"]
    return get_llm()
