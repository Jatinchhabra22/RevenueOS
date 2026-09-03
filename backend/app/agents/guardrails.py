"""Deterministic post-selection policy checks. The LLM cannot override these."""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.agent_policy import CONTACT_ACTIONS, RETRY_ACTIONS, AgentPolicy, get_agent_policy
from app.schemas.agent import CandidateAction, GuardrailResult
from app.schemas.entities import EventContext, Intervention


def _parse_ts(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def validate_guardrails(
    *,
    selected_action_id: str,
    selected_action_type: str,
    candidates: list[CandidateAction],
    context: EventContext,
    now: datetime | None = None,
    policy: AgentPolicy | None = None,
) -> GuardrailResult:
    settings = policy or get_agent_policy()
    now = now or datetime.now(timezone.utc)
    violations: list[str] = []

    candidate_ids = {item.action_id for item in candidates}
    candidate_types = {item.action_type for item in candidates}
    if selected_action_id not in candidate_ids:
        violations.append("selected action is not in the candidate list")
    if selected_action_type not in candidate_types and selected_action_id in candidate_ids:
        violations.append("selected action type does not match a candidate")
    if selected_action_type not in settings.allowed_actions:
        violations.append("action is not in the merchant allowlist")

    status = (context.event.event_status or "").lower()
    if settings.require_open_event and status not in {"open", "action_pending"} and selected_action_type != "stop_recovery":
        violations.append(f"event status '{context.event.event_status}' is not actionable")

    history = list(context.previous_interventions)
    if len(history) >= settings.max_interventions_per_event and selected_action_type != "stop_recovery":
        violations.append("maximum interventions for this event have been reached")

    retries = sum(1 for item in history if item.action_type in RETRY_ACTIONS)
    contacts = sum(1 for item in history if item.action_type in CONTACT_ACTIONS)
    if selected_action_type in RETRY_ACTIONS and retries >= settings.max_retry_actions:
        violations.append("retry limit reached")
    if selected_action_type in CONTACT_ACTIONS and contacts >= settings.max_contact_actions:
        violations.append("contact limit reached")

    last_same: Intervention | None = None
    for item in history:
        if item.action_type == selected_action_type:
            last_same = item
    selected_candidate = next((item for item in candidates if item.action_id == selected_action_id), None)
    if selected_candidate:
        for required in selected_candidate.required_inputs:
            if required == "event_id" and not context.event.event_id:
                violations.append("missing required input: event_id")
            elif required == "customer_id" and not context.event.customer_id:
                violations.append("missing required input: customer_id")

    if last_same and selected_action_type != "stop_recovery":
        last_ts = _parse_ts(last_same.action_timestamp)
        if last_ts is not None:
            elapsed = (now - last_ts).total_seconds() / 3600.0
            if elapsed < settings.cooldown_hours:
                violations.append(
                    f"cooldown active for {selected_action_type} ({elapsed:.1f}h < {settings.cooldown_hours}h)"
                )
        else:
            violations.append(f"duplicate {selected_action_type} already recorded on this event")

    if violations:
        return GuardrailResult(
            allowed=False,
            status="BLOCK",
            reason="; ".join(violations),
            violations=violations,
            reason_codes=_reason_codes(violations),
        )
    return GuardrailResult(
        allowed=True,
        status="ALLOW",
        reason="All policy checks passed",
        violations=[],
        reason_codes=["POLICY_CLEAR"],
    )


def _reason_codes(violations: list[str]) -> list[str]:
    codes: list[str] = []
    for item in violations:
        text = item.lower()
        if "not in the candidate" in text:
            codes.append("UNKNOWN_ACTION")
        elif "allowlist" in text:
            codes.append("ACTION_NOT_ALLOWED")
        elif "not actionable" in text:
            codes.append("EVENT_NOT_ACTIONABLE")
        elif "already recovered" in text or "resolved" in text:
            codes.append("EVENT_ALREADY_RECOVERED")
        elif "maximum interventions" in text:
            codes.append("MAX_INTERVENTIONS_REACHED")
        elif "retry limit" in text:
            codes.append("MAX_RETRIES_REACHED")
        elif "contact limit" in text:
            codes.append("CONTACT_LIMIT_REACHED")
        elif "cooldown" in text:
            codes.append("CONTACT_COOLDOWN_ACTIVE")
        elif "duplicate" in text:
            codes.append("DUPLICATE_INTERVENTION")
        elif "missing required" in text:
            codes.append("MISSING_REQUIRED_CONTEXT")
        else:
            codes.append("POLICY_VIOLATION")
    return codes
