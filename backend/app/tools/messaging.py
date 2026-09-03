"""Simulated customer-messaging tools."""

from __future__ import annotations

from app.schemas.agent import ToolResult
from app.schemas.entities import EventContext
from app.tools.registry import execute_simulated_action


def send_payment_reminder(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="send_email",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )


def offer_retention(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="retention_offer",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )


def no_action(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="stop_recovery",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )
