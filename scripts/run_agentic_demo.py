#!/usr/bin/env python3
"""CLI walkthrough of the agentic recovery loop on a known demo event."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a structured agentic demo")
    parser.add_argument("--event-id", default="EVT_000861")
    parser.add_argument("--data-dir", default="data/demo")
    parser.add_argument(
        "--agent-mode",
        default=None,
        help="Override AGENT_MODE for this process (ollama | deterministic_fallback | auto)",
    )
    args = parser.parse_args()
    if args.agent_mode:
        os.environ["AGENT_MODE"] = args.agent_mode

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.agents.graph import run_recovery_agent
    from app.agents.llm.runtime import agent_health_payload
    from app.services.data.context import assemble_event_context
    from app.services.data.loaders import load_directory
    from app.services.prediction.inference import predict_churn, predict_recovery
    from app.services.risk.engine import assess_revenue_risk

    settings = get_settings()
    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    tables = load_directory(data_dir)["tables"]
    context = assemble_event_context(args.event_id, tables)
    recovery = predict_recovery(context, settings.artifacts_path)
    churn = predict_churn(context, settings.artifacts_path)
    risk = assess_revenue_risk(context, recovery, churn)
    health = agent_health_payload()
    started = time.perf_counter()
    state = run_recovery_agent(
        context=context,
        tables=tables,
        artifacts_dir=settings.artifacts_path,
        recovery_prediction=recovery.model_dump(mode="json"),
        churn_prediction=churn.model_dump(mode="json"),
        risk_assessment=risk.model_dump(mode="json"),
    )
    elapsed_s = time.perf_counter() - started

    event = context.event
    selected = state.get("selected_action") or {}
    outcome = state.get("outcome") or {}
    history = state.get("iteration_history") or []
    calls = [item for item in (state.get("llm_calls") or []) if item.get("event_type") == "LLM_CALL_COMPLETED"]
    tools = [
        item.get("tool_name")
        for item in (state.get("agent_trace") or [])
        if item.get("event_type") == "TOOL_CALL"
    ]

    print("=" * 64)
    print("AI REVENUE RECOVERY — AGENTIC DEMO")
    print("=" * 64)
    print(f"Event: {event.event_id}")
    print(f"Customer: {event.customer_id}")
    print(f"Amount at risk: ₹{event.amount_at_risk:,.2f}")
    print()
    print("ML SIGNALS")
    print(f"  Recovery probability: {recovery.probability:.2%}  fallback={recovery.fallback}")
    print(f"  Churn probability:    {churn.probability:.2%}  fallback={churn.fallback}")
    print(f"  Expected recoverable: ₹{risk.expected_recovery_value:,.2f}")
    print(f"  Priority: {risk.priority_category} ({risk.priority_score:.1f})")
    print()
    print("AGENT RUNTIME")
    print(f"  Configured: {health.get('configured_mode')}")
    print(f"  Provider: {state.get('provider')}")
    print(f"  Model: {state.get('model')}")
    print(f"  Mode: {state.get('agent_mode')}")
    print(f"  Fallback: {state.get('fallback_used')}")
    print(f"  Successful LLM calls: {state.get('llm_call_count')}")
    print(f"  Wall-clock seconds: {elapsed_s:.1f}")
    print()
    print("WORKFLOW")
    stage_labels = [
        ("supervisor", "Supervisor"),
        ("investigate_context", "Investigator"),
        ("diagnose_event", "Diagnosis"),
        ("analyze_customer", "Customer Analyst"),
        ("select_action", "Strategist"),
        ("validate_guardrails", "Guardrail"),
        ("execute_action", "Execution"),
        ("monitor_result", "Observer"),
        ("reflect_outcome", "Reflection"),
    ]
    seen = {entry.get("stage") for entry in (state.get("audit_trail") or [])}
    for key, label in stage_labels:
        mark = "done" if key in seen else "—"
        print(f"  {label}: {mark}")
    print()
    print("AUDIT")
    for entry in state.get("audit_trail") or []:
        print(f"  {entry.get('stage')}: {entry.get('decision')}")
    print()
    print("LLM CALLS")
    if not calls:
        print("  (none)")
    for item in calls:
        print(
            f"  {item.get('schema_name')} success={item.get('success')} "
            f"{item.get('duration_ms')}ms"
        )
    print()
    print("TOOLS")
    print("  " + ", ".join(str(name) for name in tools if name) or "  (none)")
    print()
    print("ITERATIONS")
    if not history:
        print(f"  Iteration {state.get('iteration')}: {selected.get('action_type')} → {outcome.get('outcome')}")
    for row in history:
        print(f"  Iteration {row.get('iteration')}: {row.get('action_type')} → {row.get('outcome')}")
    print()
    print("FINAL RESULT")
    print(f"  Outcome: {outcome.get('outcome')}")
    print(f"  Amount recovered: ₹{float(outcome.get('amount_recovered') or 0):,.2f}")
    print(f"  Terminal reason: {state.get('terminal_reason') or state.get('status')}")
    print(f"  Iterations: {state.get('iteration')}")
    print(f"  Workflow: {state.get('workflow_id')}")
    print("=" * 64)


if __name__ == "__main__":
    main()
