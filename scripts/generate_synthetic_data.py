#!/usr/bin/env python3
"""Generate the reproducible synthetic merchant dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.data.synthetic import GeneratorConfig, default_output_dirs, write_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic RevenueOS datasets")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--customers", type=int, default=3000)
    args = parser.parse_args()

    synthetic_dir, demo_dir = default_output_dirs()
    metadata = write_dataset(
        synthetic_dir,
        GeneratorConfig(seed=args.seed, n_customers=args.customers),
        extra_dirs=[demo_dir],
    )
    if not metadata["validation"]["ok"]:
        print(json.dumps(metadata["validation"], indent=2))
        raise SystemExit("Synthetic dataset failed validation")
    print(json.dumps({k: metadata[k] for k in ("row_counts", "recovery_rate", "churn_rate", "random_seed")}, indent=2))
    print(f"Wrote {synthetic_dir} and {demo_dir}")


if __name__ == "__main__":
    main()
