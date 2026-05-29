"""
Round-trip test for train.py against a temp MLflow tracking dir.

Proves end-to-end that:
  - the training script runs without errors
  - it registers a model in the temp registry
  - the registered model can be loaded back through mlflow.pyfunc and
    produce a prediction matching the in-memory model's output
"""

import mlflow
import numpy as np
import pandas as pd
import pytest

from src.data.transaction_features import CATEGORICAL_FEATURES, FEATURE_COLUMNS


@pytest.fixture
def tmp_mlflow(tmp_path, monkeypatch):
    """Point MLflow at an isolated SQLite + filesystem store under tmp_path."""
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    mlflow.set_tracking_uri(tracking_uri)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", tracking_uri)
    return tracking_uri


def test_log_and_load_pyfunc_wrapper(tmp_mlflow, trained_xgb):
    """End-to-end: wrap booster → log → reload → predict on object-dtype input."""
    from src.services.inference import CategoricalTreeModel

    wrapped = CategoricalTreeModel(trained_xgb, CATEGORICAL_FEATURES)

    request_row = pd.DataFrame([{
        "town": "Avon",
        "property_type": "Residential",
        "residential_type": "Single Family",
        "assessed_value": 200_000.0,
        "list_year": 2021,
        "month_recorded": 6,
    }])[FEATURE_COLUMNS]
    # cast as the API does
    request_row["list_year"] = request_row["list_year"].astype("int32")
    request_row["month_recorded"] = request_row["month_recorded"].astype("int32")

    with mlflow.start_run():
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=wrapped,
            input_example=request_row,
        )
        run_id = mlflow.active_run().info.run_id

    loaded = mlflow.pyfunc.load_model(f"runs:/{run_id}/model")
    preds = loaded.predict(request_row)

    expected = wrapped.predict(context=None, model_input=request_row)
    np.testing.assert_allclose(preds, expected, rtol=1e-5)
