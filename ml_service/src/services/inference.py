"""
Pyfunc wrapper that re-applies `category` dtype to the configured columns
before delegating to the underlying tree model.

Why this exists: native XGBoost / LightGBM categorical support requires the
input DataFrame to have `category` dtype on the categorical columns. MLflow's
JSON-based serving format round-trips category columns as plain strings
(`object` dtype), so a vanilla `mlflow.xgboost.log_model` produces a pyfunc
that breaks the first time anyone calls it through the serving API. Wrapping
the booster in this class makes the model self-healing — callers send
strings, the wrapper casts, the booster sees categories.
"""

from __future__ import annotations

from typing import Iterable, List

import mlflow.pyfunc
import pandas as pd


class CategoricalTreeModel(mlflow.pyfunc.PythonModel):
    """Wrap an XGBoost/LightGBM sklearn estimator and cast categoricals on input."""

    def __init__(self, model, categorical_columns: Iterable[str]):
        self.model = model
        self.categorical_columns: List[str] = list(categorical_columns)

    def predict(self, context, model_input, params=None):
        if not isinstance(model_input, pd.DataFrame):
            model_input = pd.DataFrame(model_input)

        df = model_input.copy()
        for col in self.categorical_columns:
            if col in df.columns and not isinstance(df[col].dtype, pd.CategoricalDtype):
                df[col] = df[col].astype("category")

        return self.model.predict(df)
