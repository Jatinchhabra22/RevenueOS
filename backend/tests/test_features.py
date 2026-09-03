from app.services.data.context import assemble_event_context
from app.services.data.synthetic import GeneratorConfig, generate_tables
from app.services.features.constants import (
    CHURN_FEATURE_COLUMNS,
    LEAKAGE_COLUMNS,
    RECOVERY_FEATURE_COLUMNS,
)
from app.services.features.dataset import build_churn_training_set, build_recovery_training_set
from app.services.features.recovery_features import recovery_feature_frame, recovery_features_from_context


def test_recovery_feature_columns_are_stable_and_complete() -> None:
    tables = generate_tables(GeneratorConfig(seed=11, n_customers=80))
    X, y, event_ids = build_recovery_training_set(tables)
    assert list(X.columns) == list(RECOVERY_FEATURE_COLUMNS)
    assert set(X.columns).isdisjoint(LEAKAGE_COLUMNS)
    assert len(X) == len(y) == len(event_ids)
    assert y.nunique() == 2


def test_churn_feature_columns_are_stable_and_complete() -> None:
    tables = generate_tables(GeneratorConfig(seed=11, n_customers=80))
    X, y, customer_ids = build_churn_training_set(tables)
    assert list(X.columns) == list(CHURN_FEATURE_COLUMNS)
    assert "churned" not in X.columns
    assert set(X.columns).isdisjoint(LEAKAGE_COLUMNS)
    assert len(X) == len(y) == len(customer_ids) == 80


def test_missing_values_do_not_break_feature_frame() -> None:
    tables = generate_tables(GeneratorConfig(seed=4, n_customers=50))
    X, _, _ = build_recovery_training_set(tables)
    # Synthetic data intentionally blanks some fields; builders must still emit the schema.
    assert list(X.columns) == list(RECOVERY_FEATURE_COLUMNS)
    assert len(X) > 0


def test_training_and_inference_feature_parity() -> None:
    tables = generate_tables(GeneratorConfig(seed=8, n_customers=50))
    X, _, event_ids = build_recovery_training_set(tables)
    event_id = str(event_ids.iloc[0])
    context = assemble_event_context(event_id, tables)
    inferred = recovery_feature_frame([recovery_features_from_context(context)])
    assert list(inferred.columns) == list(X.columns)
    again = recovery_feature_frame([recovery_features_from_context(context)])
    assert inferred.equals(again)


def test_recovery_features_exclude_current_event_outcome() -> None:
    tables = generate_tables(GeneratorConfig(seed=8, n_customers=50))
    X, y, event_ids = build_recovery_training_set(tables)
    assert "outcome" not in X.columns
    assert "amount_recovered" not in X.columns
    assert "event_status" not in X.columns
    # Label exists separately and is not a feature.
    assert "target_recovered" not in X.columns
    assert y.name == "target_recovered"
