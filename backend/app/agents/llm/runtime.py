"""Resolve provider + transparency fields without pretending fallback is LLM."""

from __future__ import annotations

from typing import Any

from app.agents.llm.ollama_provider import OllamaLLM, ollama_available, ollama_has_model
from app.agents.llm.provider import HttpJsonLLM, StructuredLLM
from app.core.config import Settings, get_settings


def configured_agent_mode(settings: Settings | None = None) -> str:
    cfg = settings or get_settings()
    mode = (cfg.agent_mode or "auto").strip().lower()
    if mode in {"fallback", "deterministic", "deterministic_fallback"}:
        return "deterministic_fallback"
    if mode in {"ollama", "openai_compatible", "auto"}:
        return mode
    return "auto"


def bind_llm(settings: Settings | None = None) -> StructuredLLM | None:
    cfg = settings or get_settings()
    mode = configured_agent_mode(cfg)
    if mode == "deterministic_fallback":
        return None
    if mode == "ollama":
        return OllamaLLM(
            base_url=cfg.ollama_base_url,
            model=cfg.ollama_model,
            timeout=cfg.llm_timeout_seconds,
            max_retries=cfg.llm_max_retries,
        )
    if mode == "openai_compatible":
        if not cfg.llm_configured:
            return None
        return HttpJsonLLM(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
            base_url=cfg.llm_base_url,
            timeout=cfg.llm_timeout_seconds,
        )
    if cfg.llm_configured:
        return HttpJsonLLM(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
            base_url=cfg.llm_base_url,
            timeout=cfg.llm_timeout_seconds,
        )
    return None


def describe_runtime(
    llm: StructuredLLM | None,
    *,
    settings: Settings | None = None,
    injected: bool = False,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    if llm is None:
        return {
            "configured_mode": configured_agent_mode(cfg),
            "agent_mode": "deterministic_fallback",
            "provider": None,
            "model": None,
            "fallback_used": True,
            "llm_available": False,
        }
    if injected:
        model = getattr(llm, "model", None) or type(llm).__name__
        return {
            "configured_mode": configured_agent_mode(cfg),
            "agent_mode": "llm",
            "provider": "injected",
            "model": str(model),
            "fallback_used": False,
            "llm_available": True,
        }
    if isinstance(llm, OllamaLLM):
        available = ollama_available(llm.base_url)
        present = ollama_has_model(llm.base_url, llm.model) if available else False
        live = available and present
        return {
            "configured_mode": configured_agent_mode(cfg),
            "agent_mode": "ollama" if live else "deterministic_fallback",
            "provider": "ollama",
            "model": llm.model,
            "fallback_used": not live,
            "llm_available": live,
            "model_present": present,
        }
    if isinstance(llm, HttpJsonLLM):
        return {
            "configured_mode": configured_agent_mode(cfg),
            "agent_mode": "llm",
            "provider": "openai_compatible",
            "model": llm.model,
            "fallback_used": False,
            "llm_available": True,
        }
    return {
        "configured_mode": configured_agent_mode(cfg),
        "agent_mode": "llm",
        "provider": type(llm).__name__,
        "model": getattr(llm, "model", None),
        "fallback_used": False,
        "llm_available": True,
    }


def agent_health_payload() -> dict[str, Any]:
    cfg = get_settings()
    llm = bind_llm(cfg)
    info = describe_runtime(llm, settings=cfg, injected=False)
    ollama_up = ollama_available(cfg.ollama_base_url)
    return {
        "configured_mode": info["configured_mode"],
        "llm_available": bool(info.get("llm_available")),
        "provider": info.get("provider") if info.get("llm_available") else info.get("provider"),
        "model": info.get("model") or cfg.ollama_model,
        "fallback_available": True,
        "ollama_reachable": ollama_up,
        "ollama_model": cfg.ollama_model,
        "ollama_model_present": ollama_has_model(cfg.ollama_base_url, cfg.ollama_model) if ollama_up else False,
    }
