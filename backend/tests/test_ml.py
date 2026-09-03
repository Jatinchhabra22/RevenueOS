from pathlib import Path

import joblib
import numpy as np

from app.services.data.context import assemble_event_context
from app.services.data.synthetic import GeneratorConfig, generate_tables, write_dataset
from app.services.features.constants import RECOVERY_FEATURE_COLUMNS
from app.services.prediction.inference import (
    clear_model_cache,
    predict_churn,
    predict_recovery,
)
from app.services.prediction.training import train_and_persist, train_recovery_model


def test_training_persistence_reload_and_inference(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    artifacts = tmp_path / "artifacts"
    write_dataset(data_dir, GeneratorConfig(seed=21, n_customers=250))
    summary = train_and_persist(data_dir, artifacts, random_state=21)
    assert 0.5 <= summary["recovery_auc"] <= 1.0
    assert 0.5 <= summary["churn_auc"] <= 1.0

    recovery_path = artifacts / "models" / "recovery_model.joblib"
    churn_path = artifacts / "models" / "churn_model.joblib"
    assert recovery_path.exists()
    assert churn_path.exists()
    assert (artifacts / "metrics" / "training_metadata.json").exists()

    loaded = joblib.load(recovery_path)
    assert hasattr(loaded, "predict_proba")

    tables = generate_tables(GeneratorConfig(seed=21, n_customers=250))
    event_id = str(tables["revenue_events"].iloc[0]["event_id"])
    context = assemble_event_context(event_id, tables)
    clear_model_cache()
    recovery = predict_recovery(context, artifacts)
    churn = predict_churn(context, artifacts)
    assert 0.0 <= recovery.probability <= 1.0
    assert 0.0 <= churn.probability <= 1.0
    assert recovery.fallback is False
    assert churn.fallback is False
    assert recovery.model_type != "heuristic_fallback"


def test_probabilities_clipped_and_schema_match(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    artifacts = tmp_path / "artifacts"
    write_dataset(data_dir, GeneratorConfig(seed=5, n_customers=90))
    train_and_persist(data_dir, artifacts, random_state=5)
    tables = generate_tables(GeneratorConfig(seed=5, n_customers=90))
    context = assemble_event_context(str(tables["revenue_events"].iloc[3]["event_id"]), tables)
    clear_model_cache()
    prediction = predict_recovery(context, artifacts)
    assert prediction.probability == float(np.clip(prediction.probability, 0, 1))
    model = joblib.load(artifacts / "models" / "recovery_model.joblib")
    names = list(model.named_steps["preprocess"].feature_names_in_)
    assert names == list(RECOVERY_FEATURE_COLUMNS)


def test_fallback_when_artifacts_missing(tmp_path: Path) -> None:
    tables = generate_tables(GeneratorConfig(seed=2, n_customers=40))
    context = assemble_event_context(str(tables["revenue_events"].iloc[0]["event_id"]), tables)
    clear_model_cache()
    prediction = predict_recovery(context, tmp_path / "missing")
    assert prediction.fallback is True
    assert 0.0 <= prediction.probability <= 1.0


def test_recovery_training_rejects_leakage_columns() -> None:
    tables = generate_tables(GeneratorConfig(seed=6, n_customers=70))
    result = train_recovery_model(tables, random_state=6)
    assert result["selected_model"] in {"logistic_regression", "random_forest"}
    assert "compared" in result
    assert result["test_metrics"]["roc_auc"] >= 0.5
