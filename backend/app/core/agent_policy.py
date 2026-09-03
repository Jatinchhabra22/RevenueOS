"""Merchant/agent policy knobs for guardrails."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import get_settings

CONTACT_ACTIONS = frozenset(
    {
        "send_email",
        "generate_payment_link",
        "payment_method_update",
        "retention_offer",
    }
)
RETRY_ACTIONS = frozenset({"retry_now", "retry_later"})


class AgentPolicy(BaseModel):
    max_interventions_per_event: int = Field(default=3, ge=1)
    max_retry_actions: int = Field(default=3, ge=1)
    max_contact_actions: int = Field(default=3, ge=1)
    cooldown_hours: float = Field(default=24.0, ge=0)
    require_open_event: bool = True
    max_agent_iterations: int = Field(default=3, ge=1)
    allowed_actions: list[str] = Field(
        default_factory=lambda: [
            "retry_now",
            "retry_later",
            "generate_payment_link",
            "send_email",
            "payment_method_update",
            "retention_offer",
            "stop_recovery",
        ]
    )


def load_agent_policy(path: Path | None = None) -> AgentPolicy:
    settings = get_settings()
    config_path = path or (settings.repo_root / "config" / "agent_policy.json")
    payload: dict = {}
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("agent_policy.json is not valid JSON") from exc
    merchant_path = settings.data_path / "demo" / "merchant_config.json"
    if merchant_path.exists():
        try:
            merchant = json.loads(merchant_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("merchant_config.json is not valid JSON") from exc
        payload.setdefault("max_retry_actions", merchant.get("max_retry_attempts", 3))
        payload.setdefault("max_contact_actions", merchant.get("max_contact_attempts", 3))
        payload.setdefault("cooldown_hours", merchant.get("contact_cooldown_hours", 24))
    return AgentPolicy.model_validate(payload)


@lru_cache
def get_agent_policy() -> AgentPolicy:
    return load_agent_policy()
