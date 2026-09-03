"""Audit helpers and typed state accessors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas.agent import AuditEntry, CandidateAction
from app.schemas.entities import EventContext
from app.schemas.predictions import ChurnPrediction, RecoveryPrediction
from app.schemas.risk import RiskAssessment
from app.agents.state import AgentState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def append_audit(state: AgentState, stage: str, decision: str, reason: str, metadata: dict | None = None) -> list[dict[str, Any]]:
    trail = list(state.get("audit_trail") or [])
    entry = AuditEntry(
        timestamp=utcnow(),
        stage=stage,
        decision=decision,
        reason=reason,
        metadata=metadata or {},
    )
    trail.append(entry.model_dump(mode="json"))
    return trail


def require_context(state: AgentState) -> EventContext:
    payload = state.get("event_context")
    if not payload:
        raise ValueError("event_context is missing from agent state")
    return EventContext.model_validate(payload)


def optional_recovery(state: AgentState) -> RecoveryPrediction | None:
    payload = state.get("recovery_prediction")
    return RecoveryPrediction.model_validate(payload) if payload else None


def optional_churn(state: AgentState) -> ChurnPrediction | None:
    payload = state.get("churn_prediction")
    return ChurnPrediction.model_validate(payload) if payload else None


def parse_candidates(state: AgentState) -> list[CandidateAction]:
    return [CandidateAction.model_validate(item) for item in state.get("candidate_actions") or []]
