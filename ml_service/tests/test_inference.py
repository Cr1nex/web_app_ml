"""
Tests for the CategoricalTreeModel pyfunc wrapper.

The wrapper exists so MLflow's JSON serving round-trip (which strips
`category` dtype back to `object`) doesn't break xgboost at inference
time. These tests prove the cast is applied on the boundary.
"""

import pandas as pd

from src.data.transaction_features import CATEGORICAL_FEATURES, FEATURE_COLUMNS
from src.services.inference import CategoricalTreeModel


def _request_row():
    return {
        "town": "Avon",
        "property_type": "Residential",
        "residential_type": "Single Family",
        "assessed_value": 200_000.0,
        "list_year": 2021,
        "month_recorded": 6,
    }


def test_wrapper_accepts_object_dtype(trained_xgb):
    """Object-dtype input (post-JSON) goes in, a finite prediction comes out."""
    wrapped = CategoricalTreeModel(trained_xgb, CATEGORICAL_FEATURES)
    df = pd.DataFrame([_request_row()])[FEATURE_COLUMNS]
    # explicit string dtype to simulate what FastAPI hands us after JSON parse
    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].astype("string")

    preds = wrapped.predict(context=None, model_input=df)

    assert len(preds) == 1
    assert preds[0] > 0
    assert preds[0] == preds[0]  # not NaN


def test_wrapper_idempotent_on_category_dtype(trained_xgb):
    """Already-category input passes through unchanged."""
    wrapped = CategoricalTreeModel(trained_xgb, CATEGORICAL_FEATURES)
    df = pd.DataFrame([_request_row()])[FEATURE_COLUMNS]
    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].astype("category")

    preds = wrapped.predict(context=None, model_input=df)

    assert len(preds) == 1


def test_wrapper_handles_batch(trained_xgb):
    """Batch of N rows yields N predictions."""
    wrapped = CategoricalTreeModel(trained_xgb, CATEGORICAL_FEATURES)
    df = pd.DataFrame([_request_row()] * 5)[FEATURE_COLUMNS]
    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].astype("string")

    preds = wrapped.predict(context=None, model_input=df)

    assert len(preds) == 5
