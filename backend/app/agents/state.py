"""Typed LangGraph state for one bounded recovery workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    workflow_id: str
    thread_id: str
    event_id: str
    customer_id: str
    event_context: dict[str, Any]
    investigation: dict[str, Any]
    diagnosis: dict[str, Any]
    customer_analysis: dict[str, Any]
    recovery_prediction: dict[str, Any]
    churn_prediction: dict[str, Any]
    risk_assessment: dict[str, Any]
    candidate_actions: list[dict[str, Any]]
    strategy: dict[str, Any]
    selected_action: dict[str, Any]
    decision: dict[str, Any]
    guardrail_result: dict[str, Any]
    tool_result: dict[str, Any]
    outcome: dict[str, Any]
    reflection: dict[str, Any]
    iteration_history: list[dict[str, Any]]
    agent_trace: list[dict[str, Any]]
    audit_trail: list[dict[str, Any]]
    status: str
    workflow_status: str
    next_step: str
    supervisor_route: str
    terminal_reason: str
    iteration: int
    max_iterations: int
    used_llm: bool
    llm_calls: list[dict[str, Any]]
    llm_call_count: int
    agent_mode: str
    provider: str | None
    model: str | None
    error: str
    avoid_actions: list[str]
    recoverability: dict[str, Any]
