#!/usr/bin/env python3
"""Write small CSV-only packs under data/upload-tests for the Data screen upload flow."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.data.synthetic import GeneratorConfig, write_dataset  # noqa: E402

PACKS = (
    (
        "tiny_40_customers",
        "Fastest upload check. Compare Data page counts to expected_counts.json.",
        GeneratorConfig(seed=801, n_customers=40, merchant_id="MERCHANT_UPLOAD_TINY"),
    ),
    (
        "small_100_customers",
        "Slightly larger book so Opportunities has more open events.",
        GeneratorConfig(seed=802, n_customers=100, merchant_id="MERCHANT_UPLOAD_SMALL"),
    ),
    (
        "mid_80_customers",
        "Independent 80-customer book for a second upload pass.",
        GeneratorConfig(seed=803, n_customers=80, merchant_id="MERCHANT_UPLOAD_UPI"),
    ),
)

TABLES = (
    "customers",
    "transactions",
    "subscriptions",
    "revenue_events",
    "intervention_history",
)


def _row_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def main() -> int:
    root = ROOT / "data" / "upload-tests"
    root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for name, description, config in PACKS:
        dest = root / name
        metadata = write_dataset(dest, config)
        if not metadata["validation"]["ok"]:
            print(json.dumps(metadata["validation"], indent=2))
            raise SystemExit(f"{name} failed validation")
        counts = {table: _row_count(dest / f"{table}.csv") for table in TABLES}
        events = pd.read_csv(dest / "revenue_events.csv")
        payload = {
            "folder": name,
            "description": description,
            "merchant_id": config.merchant_id,
            "seed": config.seed,
            "csv_files": [f"{table}.csv" for table in TABLES],
            "row_counts": counts,
            "open_events": int((events["event_status"].astype(str).str.lower() == "open").sum()),
        }
        (dest / "expected_counts.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        rows.append(payload)
        print(json.dumps({"folder": name, **counts, "open_events": payload["open_events"]}, indent=2))

    (root / "MANIFEST.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (root / "README.md").write_text(
        "\n".join(
            [
                "# Upload-test CSV packs",
                "",
                "Use these folders to check that **Data → Upload** replaces the active book",
                "and that the Data / Overview / Opportunities counts match the CSVs.",
                "",
                "Do **not** upload `metadata.json` or `merchant_config.json`. Upload only the five CSVs.",
                "",
                "## How to test",
                "",
                "1. Open http://localhost:5173 and sign in (`demo@revenueos` / `RevenueOS-Demo`).",
                "2. Go to **Data**.",
                "3. Choose **all five** CSVs from **one** folder:",
                "",
                "   - `customers.csv`",
                "   - `transactions.csv`",
                "   - `subscriptions.csv`",
                "   - `revenue_events.csv`",
                "   - `intervention_history.csv`",
                "",
                "4. Click **Upload and validate**.",
                "5. On Data, Customers / Transactions / Subscriptions / Revenue events /",
                "   Interventions / Open events must match that folder's `expected_counts.json`.",
                "6. Open **Opportunities**. The list length should equal **Open events**",
                "   (or the page total).",
                "7. Restore the seeded demo: restart the API, or upload the five CSVs from `data/demo`.",
                "",
                "## Folders",
                "",
                "- `tiny_40_customers` — smallest; best first test",
                "- `small_100_customers` — more opportunities",
                "- `mid_80_customers` — third independent seed, 80 customers",
                "",
                "Regenerate: `python scripts/generate_upload_test_datasets.py`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
