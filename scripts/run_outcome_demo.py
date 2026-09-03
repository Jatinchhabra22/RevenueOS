#!/usr/bin/env python3
"""Run several simulated recoveries and print DEMO outcome intelligence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.schemas.api import AgentRunRequest  # noqa: E402
from app.services.agent_runs import run_event_agent  # noqa: E402
from app.services.outcomes import (  # noqa: E402
    action_effectiveness,
    aggregate_outcomes,
    load_outcome_records,
    segment_intelligence,
)
from app.services.runtime import AppRuntime  # noqa: E402


def _inr(value: float) -> str:
    return f"₹{value:,.0f}"


def _open_event_ids(tables: dict, preferred: str, limit: int) -> list[str]:
    events = tables["revenue_events"]
    if "event_status" in events.columns:
        events = events[events["event_status"].astype(str).str.lower() == "open"]
    ids = [str(value) for value in events["event_id"].tolist()]
    ordered: list[str] = []
    if preferred in ids:
        ordered.append(preferred)
    ordered.extend(item for item in ids if item not in ordered)
    return ordered[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo outcome intelligence from simulated agent runs.")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--event-id", default="EVT_000861")
    args = parser.parse_args()

    settings = get_settings()
    runtime = AppRuntime.from_settings(settings, disable_llm=True)
    tables = runtime.tables()
    event_ids = _open_event_ids(tables, args.event_id, args.limit)

    print("=" * 64)
    print("AGENT OUTCOME INTELLIGENCE  —  DEMO OBSERVATIONS ONLY")
    print("Not universal claims. Not dataset ground-truth labels.")
    print("=" * 64)
    print()
    print(f"Running {len(event_ids)} simulated agent executions…")
    print()

    for event_id in event_ids:
        result = run_event_agent(runtime, event_id, AgentRunRequest())
        expected = result.risk_assessment.expected_recovery_value
        observed = result.outcome.amount_recovered if result.outcome else 0.0
        print(
            f"  {event_id}  {result.selected_action.action_type:24}  "
            f"{result.outcome.outcome if result.outcome else '—':14}  "
            f"expected {_inr(expected)}  observed {_inr(observed)}"
        )
        if result.decision.historical_note:
            print(f"    {result.decision.historical_note}")

    records = load_outcome_records(runtime)
    metrics = aggregate_outcomes(records)
    actions = action_effectiveness(records)
    segments = segment_intelligence(records)

    print()
    print("-" * 64)
    print("AGGREGATE (observed agent outcomes)")
    print(f"Executions: {metrics.executions}")
    print(f"Recovered: {metrics.successful_recoveries}")
    print(f"Not recovered: {metrics.unsuccessful_recoveries}")
    print(f"Pending: {metrics.pending_outcomes}  Blocked: {metrics.blocked_actions}")
    rate = f"{metrics.recovery_rate:.0%}" if metrics.recovery_rate is not None else "n/a"
    print(f"Recovery Rate (resolved attempts): {rate}")
    print(f"Amount Recovered: {_inr(metrics.total_amount_recovered)}")
    print(f"Amount Attempted: {_inr(metrics.total_amount_attempted)}")
    print(f"Expected recovery (resolved): {_inr(metrics.expected_recovery_sum)}")
    print(f"Observed recovery (resolved): {_inr(metrics.observed_recovery_sum)}")
    print()
    print("TOP ACTIONS")
    for row in actions.items[:5]:
        sample = "  [Low sample size]" if row.low_sample_size else ""
        rate_s = f"{row.recovery_rate:.0%}" if row.recovery_rate is not None else "n/a"
        print(f"  {row.action_type}")
        print(f"    Recovery: {rate_s}  Executions: {row.execution_count}  Amount: {_inr(row.amount_recovered)}{sample}")
        print(
            f"    Observed {_inr(row.observed_recovery)} vs expected {_inr(row.expected_recovery_value)}"
        )
    print()
    print("LEARNING SIGNALS (contextual evidence — not policy updates)")
    if not segments.learning_signals:
        print("  None yet.")
    by_segment: dict[str, list] = {}
    for signal in segments.learning_signals:
        by_segment.setdefault(signal.segment, []).append(signal)
    for segment, rows in list(by_segment.items())[:8]:
        ranked = sorted(rows, key=lambda item: (item.observed_recovery_rate or -1, item.observations), reverse=True)
        best = ranked[0]
        print(f"  {segment}:")
        print(f"    {best.action_type} appears strongest in this demo")
        print(
            f"    Observations: {best.observations}  "
            f"Rate: {best.observed_recovery_rate:.0%}  "
            f"Confidence: {best.confidence}  Quality: {best.sample_quality}"
            if best.observed_recovery_rate is not None
            else f"    Observations: {best.observations}  Confidence: {best.confidence}"
        )
    print()
    if segments.observations:
        print("SEGMENT NOTES")
        for note in segments.observations:
            print(f"  - {note}")
    print()
    print("These figures come from simulated DEMO executions.")
    print("They do not retrain models or rewrite config/agent_policy.json.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
