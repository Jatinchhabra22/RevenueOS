from pathlib import Path

import pandas as pd

from app.services.data.synthetic import GeneratorConfig, generate_tables, write_dataset
from app.services.data.validation import validate_dataset


def test_generation_is_reproducible() -> None:
    cfg = GeneratorConfig(seed=42, n_customers=120)
    first = generate_tables(cfg)
    second = generate_tables(cfg)
    pd.testing.assert_frame_equal(first["customers"], second["customers"])
    pd.testing.assert_frame_equal(first["transactions"], second["transactions"])
    pd.testing.assert_frame_equal(first["revenue_events"], second["revenue_events"])
    pd.testing.assert_frame_equal(first["intervention_history"], second["intervention_history"])


def test_validation_passes_and_relationships_hold() -> None:
    tables = generate_tables(GeneratorConfig(seed=7, n_customers=200))
    report = validate_dataset(**tables)
    assert report["ok"], report["errors"]
    assert 2000 <= report["row_counts"]["transactions"] or report["row_counts"]["transactions"] > 400
    assert report["row_counts"]["revenue_events"] > 20
    assert report["row_counts"]["customers"] == 200


def test_labels_are_structured_not_independent() -> None:
    tables = generate_tables(GeneratorConfig(seed=42, n_customers=400))
    customers = tables["customers"]
    high_success = customers["payment_success_rate"] >= customers["payment_success_rate"].median()
    churn_high_success = float(customers.loc[high_success, "churned"].mean())
    churn_low_success = float(customers.loc[~high_success, "churned"].mean())
    assert churn_low_success > churn_high_success

    events = tables["revenue_events"]
    history = tables["intervention_history"].merge(
        events[["event_id", "failure_reason"]],
        on="event_id",
        how="left",
    )
    expired = history["failure_reason"].eq("card_expired")
    if int(expired.sum()) >= 20:
        update_rate = float(
            history.loc[expired & history["action_type"].eq("payment_method_update"), "outcome"].eq("recovered").mean()
        )
        retry_rate = float(
            history.loc[expired & history["action_type"].eq("retry_now"), "outcome"].eq("recovered").mean()
        )
        if pd.notna(update_rate) and pd.notna(retry_rate):
            assert update_rate >= retry_rate


def test_write_dataset_creates_required_files(tmp_path: Path) -> None:
    extra = tmp_path / "demo"
    metadata = write_dataset(
        tmp_path / "synthetic",
        GeneratorConfig(seed=1, n_customers=40),
        extra_dirs=[extra],
    )
    assert metadata["validation"]["ok"]
    for folder in (tmp_path / "synthetic", extra):
        for name in (
            "customers.csv",
            "transactions.csv",
            "subscriptions.csv",
            "revenue_events.csv",
            "intervention_history.csv",
            "metadata.json",
            "merchant_config.json",
        ):
            assert (folder / name).exists()
