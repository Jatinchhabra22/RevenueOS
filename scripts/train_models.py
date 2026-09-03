#!/usr/bin/env python3
"""Train recovery and churn models from a canonical dataset directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.services.prediction.training import train_and_persist  # noqa: E402


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Train RevenueOS recovery and churn models")
    parser.add_argument("--data-dir", type=Path, default=settings.data_path / "demo")
    parser.add_argument("--artifacts-dir", type=Path, default=settings.artifacts_path)
    parser.add_argument("--seed", type=int, default=settings.random_seed)
    args = parser.parse_args()

    summary = train_and_persist(args.data_dir, args.artifacts_dir, args.seed)
    print(json.dumps(summary, indent=2))
    if summary["recovery_leakage_warning"] or summary["churn_leakage_warning"]:
        print("Warning: test ROC-AUC is very high; inspect features for leakage before treating this as production quality.")


if __name__ == "__main__":
    main()
