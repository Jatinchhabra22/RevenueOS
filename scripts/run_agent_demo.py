#!/usr/bin/env python3
"""Run the recovery agent on a small set of open demo events."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.graph import run_recovery_agent  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.data.context import assemble_event_context  # noqa: E402
from app.services.data.loaders import load_directory  # noqa: E402
from app.services.prediction.inference import clear_model_cache  # noqa: E402


def _open_event_ids(tables: dict, preferred: str, limit: int) -> list[str]:
    events = tables["revenue_events"]
    if "event_status" in events.columns:
        events = events[events["event_status"].astype(str).str.lower() == "open"]
    ids = [str(value) for value in events["event_id"].tolist()]
    ordered = []
    if preferred in ids:
        ordered.append(preferred)
    ordered.extend(item for item in ids if item not in ordered)
    return ordered[:limit]


def _inr(value: float) -> str:
    return f"₹{value:,.0f}"


def print_result(state: dict) -> None:
    ctx = state["event_context"]["event"]
    rec = state["recovery_prediction"]
    churn = state["churn_prediction"]
    risk = state["risk_assessment"]
    diagnosis = state["diagnosis"]
    print("=" * 60)
    print(f"Event: {ctx['event_id']}")
    print(f"Amount at Risk: {_inr(ctx['amount_at_risk'])}")
    print(f"Failure: {ctx.get('failure_reason')}")
    print(f"Recovery Probability: {rec['probability']:.0%}")
    print(f"Churn Probability: {churn['probability']:.0%}")
    print(f"Expected Recovery Value: {_inr(risk['expected_recovery_value'])}")
    print(f"Priority: {risk['priority_category']} ({risk['priority_score']:.1f})")
    print()
    print("Diagnosis:")
    print(f"  {diagnosis['event_summary']}")
    print(f"  Strategy: {diagnosis['recommended_strategy']}")
    print(f"  Source: {diagnosis['source']}")
    print()
    print("Candidate Actions:")
    for item in state["candidate_actions"]:
        marker = "*" if item["action_id"] == state["selected_action"]["action_id"] else "-"
        print(f"  {marker} {item['action_type']}: {item['rationale']}")
    print()
    print(f"Selected Action: {state['selected_action']['action_type']}")
    print(f"  Reason: {state['decision']['reason']}")
    print(f"  Source: {state['decision']['source']}")
    print()
    print(f"Guardrail: {state['guardrail_result']['status']}")
    print(f"  {state['guardrail_result']['reason']}")
    if state.get("tool_result"):
        print()
        print(f"Execution: {state['tool_result']['status']} ({state['tool_result']['execution_id']})")
        print(f"  {state['tool_result']['message']}")
    print()
    print(f"Outcome: {state['outcome']['outcome']}")
    print(f"  Amount recovered: {_inr(state['outcome']['amount_recovered'])}")
    print(f"  Remaining at risk: {_inr(state['outcome']['remaining_amount_at_risk'])}")
    print()
    print(f"Final Decision: {state['status']}")
    print("=" * 60)
    print()


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run LangGraph recovery agent demo")
    parser.add_argument("--data-dir", type=Path, default=settings.data_path / "demo")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--event-id", type=str, default=None)
    args = parser.parse_args()

    clear_model_cache()
    tables = load_directory(args.data_dir)["tables"]
    if args.event_id:
        event_ids = [args.event_id]
    else:
        event_ids = _open_event_ids(tables, "EVT_000861", args.limit)

    summaries = []
    for event_id in event_ids:
        context = assemble_event_context(event_id, tables)
        state = run_recovery_agent(
            event_id=event_id,
            context=context,
            tables=tables,
            artifacts_dir=settings.artifacts_path,
        )
        print_result(state)
        summaries.append(
            {
                "event_id": event_id,
                "priority": state["risk_assessment"]["priority_category"],
                "selected_action": state["selected_action"]["action_type"],
                "guardrail": state["guardrail_result"]["status"],
                "outcome": state["outcome"]["outcome"],
                "status": state["status"],
            }
        )

    out = settings.artifacts_path / "metrics" / "agent_demo_summary.json"
    out.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
