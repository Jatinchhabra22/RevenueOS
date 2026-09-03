# Extra merchant datasets

These packs are **valid** synthetic merchant books. They do **not** replace
`data/demo` until you upload them on the Data screen.

Use them to:

- smoke-test ingest at different sizes
- optionally retrain models on `train_holdout_seed303` (`python scripts/train_models.py --data-dir data/new-data/train_holdout_seed303`)
- give the recovery agent distinct rails (UPI vs expired cards vs VIP churn vs prior interventions)

Each folder contains the five CSVs plus `metadata.json` and `merchant_config.json`.

## How to test

1. Start the API and UI.
2. Sign in with the demo credentials.
3. Open **Data**.
4. Multi-select the five CSV files from **one** folder below.
5. Upload. Overview / Opportunities should reflect the new counts.
6. Run the recovery agent on an open HIGH event in that book.
7. Restore the seeded demo by restarting the API or re-uploading `data/demo`.

## Packs

- `compact_seed7` — Small balanced book. Fast upload and UI smoke tests.
- `midmarket_seed101` — Medium balanced book for ranking and scoring time checks.
- `high_volume_seed202` — Larger balanced book. Check opportunity list performance.
- `train_holdout_seed303` — Independent seed for optional model retraining — does not replace data/demo.
- `eval_compact_seed404` — Small evaluation book after training on another pack.
- `scenario_upi_rail_seed501` — UPI-heavy timeouts and UPI failures. Agent should prefer retries / payment links.
- `scenario_expired_cards_seed502` — Card-expired subscription book. Agent should prefer payment method update.
- `scenario_vip_churn_seed503` — High LTV, elevated churn. Customer analyst + retention-sensitive strategies.
- `scenario_open_history_seed504` — Open events that already have failed interventions. Guardrails, cooldown, reflection.

Regenerate: `python scripts/generate_test_datasets.py`

`data/demo` (seed 42, 3,000 customers) remains the default console and EVT_000861 walkthrough.
