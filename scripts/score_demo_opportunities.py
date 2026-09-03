#!/usr/bin/env python3
"""Score demo revenue events with trained models and the risk engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.data.loaders import load_directory  # noqa: E402
from app.services.prediction.inference import clear_model_cache  # noqa: E402
from app.services.risk.batch import score_events, summarize_assessments  # noqa: E402


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Rank demo recovery opportunities")
    parser.add_argument("--data-dir", type=Path, default=settings.data_path / "demo")
    parser.add_argument("--artifacts-dir", type=Path, default=settings.artifacts_path)
    parser.add_argument("--status", choices=("open", "all"), default="open")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    clear_model_cache()
    tables = load_directory(args.data_dir)["tables"]
    assessments = score_events(
        tables,
        status_filter=args.status,  # type: ignore[arg-type]
        artifacts_dir=args.artifacts_dir,
        limit=args.limit,
    )
    summary = summarize_assessments(assessments)
    out = settings.artifacts_path / "metrics" / "risk_demo_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
