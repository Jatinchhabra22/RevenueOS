# Upload-test CSV packs

Use these folders to check that **Data → Upload** replaces the active book
and that the Data / Overview / Opportunities counts match the CSVs.

Do **not** upload `metadata.json` or `merchant_config.json`. Upload only the five CSVs.

## How to test

1. Open http://localhost:5173 and sign in (`demo@revenueos` / `RevenueOS-Demo`).
2. Go to **Data**.
3. Choose **all five** CSVs from **one** folder:

   - `customers.csv`
   - `transactions.csv`
   - `subscriptions.csv`
   - `revenue_events.csv`
   - `intervention_history.csv`

4. Click **Upload and validate**.
5. On Data, Customers / Transactions / Subscriptions / Revenue events /
   Interventions / Open events must match that folder's `expected_counts.json`.
6. Open **Opportunities**. The list length should equal **Open events**
   (or the page total).
7. Restore the seeded demo: restart the API, or upload the five CSVs from `data/demo`.

## Folders

- `tiny_40_customers` — smallest; best first test
- `small_100_customers` — more opportunities
- `mid_80_customers` — third independent seed, 80 customers

Regenerate: `python scripts/generate_upload_test_datasets.py`
