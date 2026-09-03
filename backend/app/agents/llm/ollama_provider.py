"""Local Ollama chat provider. Never executes model-produced code."""

from __future__ import annotations

from typing import Any

import httpx

from app.agents.llm.structured import LLMError, parse_json_object


class OllamaLLM:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float = 45.0,
        max_retries: int = 1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max(0, max_retries)

    def generate_structured(self, *, system: str, user: str, schema_name: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        body = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {
                    "role": "system",
                    "content": f"{system}\nReturn ONLY valid JSON for schema {schema_name}.",
                },
                {"role": "user", "content": user},
            ],
        }
        last_error = "LLM request failed"
        attempts = self.max_retries + 1
        for _ in range(attempts):
            try:
                response = httpx.post(url, json=body, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                content = ""
                if isinstance(data, dict):
                    message = data.get("message") or {}
                    content = str(message.get("content") or data.get("response") or "")
                return parse_json_object(content)
            except LLMError as exc:
                last_error = str(exc) or last_error
            except httpx.TimeoutException:
                last_error = "LLM request timed out"
            except Exception:
                last_error = "LLM request failed"
        raise LLMError(last_error)


def ollama_available(base_url: str, timeout: float = 1.5) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def ollama_has_model(base_url: str, model: str, timeout: float = 1.5) -> bool:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        names = [str(item.get("name") or "") for item in payload.get("models") or []]
        return any(model == name or name.startswith(f"{model}:") or name.startswith(model) for name in names)
    except Exception:
        return False
