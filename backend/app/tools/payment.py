"""Simulated payment tools. Interfaces are stable for later real integrations."""

from __future__ import annotations

from app.schemas.agent import ToolResult
from app.schemas.entities import EventContext
from app.tools.registry import execute_simulated_action


def retry_payment(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
    delayed: bool = False,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="retry_later" if delayed else "retry_now",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )


def send_payment_link(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="generate_payment_link",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )


def request_payment_method_update(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="payment_method_update",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )


def offer_grace_period(
    *,
    action_id: str,
    context: EventContext,
    recovery_probability: float,
    workflow_id: str,
) -> ToolResult:
    return execute_simulated_action(
        action_id=action_id,
        action_type="retry_later",
        context=context,
        recovery_probability=recovery_probability,
        workflow_id=workflow_id,
    )
