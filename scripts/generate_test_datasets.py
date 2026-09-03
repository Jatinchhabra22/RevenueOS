#!/usr/bin/env python3
"""Write extra valid merchant packs under data/new-data for manual upload testing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.data.synthetic import GeneratorConfig, write_dataset  # noqa: E402

PACKS = (
    ("compact_seed7", GeneratorConfig(seed=7, n_customers=80, merchant_id="MERCHANT_QA_COMPACT")),
    ("midmarket_seed101", GeneratorConfig(seed=101, n_customers=400, merchant_id="MERCHANT_QA_MID")),
    ("high_volume_seed202", GeneratorConfig(seed=202, n_customers=1200, merchant_id="MERCHANT_QA_HV")),
)


def main() -> int:
    root = ROOT / "data" / "new-data"
    root.mkdir(parents=True, exist_ok=True)
    index = []
    for name, config in PACKS:
        dest = root / name
        metadata = write_dataset(dest, config)
        if not metadata["validation"]["ok"]:
            print(json.dumps(metadata["validation"], indent=2))
            raise SystemExit(f"{name} failed validation")
        summary = {
            "folder": name,
            "seed": config.seed,
            "customers": metadata["row_counts"]["customers"],
            "revenue_events": metadata["row_counts"]["revenue_events"],
            "recovery_rate": metadata["recovery_rate"],
            "churn_rate": metadata["churn_rate"],
            "ok": True,
        }
        index.append(summary)
        print(json.dumps(summary, indent=2))
    (root / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    readme = ROOT / "data" / "new-data" / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Extra test datasets",
                "",
                "These packs are **valid** synthetic merchant books for manual upload tests.",
                "They do **not** replace `data/demo` until you upload them in the Data screen.",
                "",
                "Each folder contains:",
                "",
                "- `customers.csv`",
                "- `transactions.csv`",
                "- `subscriptions.csv`",
                "- `revenue_events.csv`",
                "- `intervention_history.csv`",
                "- `metadata.json`",
                "- `merchant_config.json`",
                "",
                "## How to test",
                "",
                "1. Start the API and UI.",
                "2. Sign in with the demo credentials.",
                "3. Open **Data**.",
                "4. Multi-select the five CSV files from **one** folder below.",
                "5. Upload. Overview / Opportunities should reflect the new counts.",
                "6. To restore the seeded demo book, restart the API (it reloads `data/demo`) or re-upload `data/demo`.",
                "",
                "## Packs",
                "",
                "- `compact_seed7` — small (80 customers). Fast to inspect.",
                "- `midmarket_seed101` — medium (400 customers).",
                "- `high_volume_seed202` — larger (1,200 customers). Check scoring time.",
                "",
                "Regenerate: `python scripts/generate_test_datasets.py`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
