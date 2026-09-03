#!/usr/bin/env python3
"""Exercise the Phase 7 API in-process (no live server required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _print_section(title: str, payload) -> None:
    print("=" * 60)
    print(title)
    print("=" * 60)
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, default=str)[:4000])
    else:
        print(payload)
    print()


def main() -> None:
    client = TestClient(app)
    health = client.get("/api/v1/health")
    _print_section("Health", health.json())

    summary = client.get("/api/v1/data/summary")
    _print_section("Dataset summary", summary.json())

    opportunities = client.get("/api/v1/opportunities", params={"limit": 5, "status": "open"})
    body = opportunities.json()
    _print_section(
        "Opportunities",
        {
            "total": body.get("total"),
            "limit": body.get("limit"),
            "offset": body.get("offset"),
            "top": body.get("items", [])[:5],
        },
    )

    event_id = (body.get("items") or [{}])[0].get("event_id") or "EVT_000861"
    detail = client.get(f"/api/v1/events/{event_id}")
    detail_json = detail.json()
    _print_section(
        f"Event detail {event_id}",
        {
            "status": detail_json.get("status"),
            "amount_at_risk": (detail_json.get("event") or {}).get("amount_at_risk"),
            "priority": (detail_json.get("risk_assessment") or {}).get("priority_category"),
            "recovery_probability": (detail_json.get("recovery_prediction") or {}).get("probability"),
        },
    )

    run = client.post(f"/api/v1/events/{event_id}/agent/run", json={"force_recompute": False})
    run_json = run.json()
    _print_section(
        "Agent run",
        {
            "workflow_id": run_json.get("workflow_id"),
            "selected_action": (run_json.get("selected_action") or {}).get("action_type"),
            "guardrail": (run_json.get("guardrail_result") or {}).get("status"),
            "outcome": (run_json.get("outcome") or {}).get("outcome"),
            "final_decision": run_json.get("final_decision"),
            "used_llm": run_json.get("used_llm"),
        },
    )

    latest = client.get(f"/api/v1/events/{event_id}/agent/latest")
    _print_section("Latest workflow", {"status": latest.status_code, "workflow_id": latest.json().get("workflow_id")})

    metrics = client.get("/api/v1/metrics/overview")
    _print_section("Metrics overview", metrics.json())

    print("OpenAPI: GET /docs")
    print("Server: uvicorn app.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
