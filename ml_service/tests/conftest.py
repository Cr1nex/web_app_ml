"""
Shared fixtures for the ml_service test suite.

Most tests don't need MLflow or the real raw CSV — they synthesise a small
in-memory DataFrame that matches the schema of the processed feature
parquet so the pipeline, training, wrapper, and API can all be exercised
without a multi-GB download.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Disable backend auth so tests don't need a Redis JWKS handshake.
os.environ.setdefault("ML_AUTH_ENABLE_AUTH", "false")


@pytest.fixture(scope="session")
def synthetic_transactions() -> pd.DataFrame:
    """A small but realistic per-transaction feature matrix."""
    rng = np.random.default_rng(seed=42)
    n = 400
    towns = rng.choice(["Avon", "Hartford", "Stamford", "Greenwich"], size=n)
    prop_types = rng.choice(["Residential", "Commercial", "Vacant Land"], size=n, p=[0.8, 0.15, 0.05])
    res_types = rng.choice(["Single Family", "Condo", "Two Family", "Unknown"], size=n, p=[0.6, 0.2, 0.15, 0.05])
    assessed = rng.uniform(80_000, 600_000, size=n)
    # Sale price loosely tracks assessed value with town noise.
    sale = assessed / 0.7 * rng.normal(1.0, 0.12, size=n)
    list_year = rng.integers(2015, 2024, size=n)
    month = rng.integers(1, 13, size=n)
    dates = pd.to_datetime({"year": list_year, "month": month, "day": rng.integers(1, 28, size=n)})

    df = pd.DataFrame({
        "date_recorded": dates,
        "town": pd.Categorical(towns),
        "property_type": pd.Categorical(prop_types),
        "residential_type": pd.Categorical(res_types),
        "assessed_value": assessed.astype("float64"),
        "list_year": list_year.astype("int16"),
        "month_recorded": month.astype("int16"),
        "sale_amount": sale.astype("float64"),
    }).sort_values("date_recorded").reset_index(drop=True)
    return df


@pytest.fixture(scope="session")
def trained_xgb(synthetic_transactions):
    """Fit a tiny XGBoost model on the synthetic data — used by wrapper + API tests."""
    import xgboost as xgb

    from src.data.transaction_features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, TARGET

    df = synthetic_transactions
    X = df[FEATURE_COLUMNS].copy()
    for col in CATEGORICAL_FEATURES:
        X[col] = X[col].astype("category")
    y = df[TARGET]

    model = xgb.XGBRegressor(
        n_estimators=20,
        max_depth=3,
        learning_rate=0.2,
        enable_categorical=True,
        tree_method="hist",
        n_jobs=1,
        random_state=0,
    )
    model.fit(X, y)
    return model
