"""
Train the per-transaction Property Valuation model and log to MLflow.

Each training row is a single real-estate transaction; the target is the
realised `sale_amount`. Features are the handful of fields a frontend user
can actually supply (see `src/data/transaction_features.py`).

Usage:
    python -m src.services.train                       # XGBoost baseline
    python -m src.services.train --model-type lightgbm
    python -m src.services.train --cv                  # add TimeSeriesSplit CV
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.lightgbm
import mlflow.xgboost
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    DEFAULT_LIGHTGBM_PARAMS,
    DEFAULT_XGBOOST_PARAMS,
    EXPERIMENT_NAME,
    MLFLOW_TRACKING_URI,
    MODEL_NAME,
    TIME_SERIES_CV_SPLITS,
    TRAIN_END_DATE,
    VALIDATION_END_DATE,
)
from src.data.transaction_features import (
    CATEGORICAL_FEATURES,
    DATE,
    FEATURE_COLUMNS,
    TARGET,
    chronological_split,
    load_or_build,
)
from src.services.inference import CategoricalTreeModel
from src.services.model import evaluate_model, get_feature_importance, get_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# Kept for backward compatibility with monitor.py / tune.py imports.
MONTHLY_TARGET = TARGET


def load_features() -> pd.DataFrame:
    """Load the per-transaction feature matrix, building it if needed."""
    return load_or_build()


def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """Return the model's input columns."""
    return [c for c in FEATURE_COLUMNS if c in df.columns]


def _build_model_params(model_type: str) -> dict:
    """Add categorical-handling flags on top of the configured base params."""
    if model_type == "xgboost":
        params = DEFAULT_XGBOOST_PARAMS.copy()
        params["enable_categorical"] = True
        params["tree_method"] = "hist"
    else:
        params = DEFAULT_LIGHTGBM_PARAMS.copy()
    return params


def _fit(model, model_type: str, X_train, y_train, X_val, y_val):
    """Fit with the framework-specific categorical hook."""
    if model_type == "lightgbm":
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            categorical_feature=CATEGORICAL_FEATURES,
        )
    else:
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model


def plot_feature_importance(importance_df: pd.DataFrame, output_path: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(importance_df["feature"], importance_df["importance"], color="#2196F3")
    ax.set_xlabel("Importance")
    ax.set_title("Feature importance")
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_predictions(y_true, y_pred, output_path: str) -> str:
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(y_true, y_pred, alpha=0.2, s=8, color="#4CAF50")
    lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    ax.plot(lims, lims, "r--", linewidth=1, label="Perfect prediction")
    ax.set_xlabel("Actual sale price ($)")
    ax.set_ylabel("Predicted sale price ($)")
    ax.set_title("Actual vs. predicted")
    ax.legend()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def train_baseline(model_type: str = "xgboost", use_cv: bool = False):
    """Train, evaluate, log artifacts, and register the model."""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    df = load_features()
    feature_cols = get_feature_columns(df)
    logger.info(f"Using {len(feature_cols)} features: {feature_cols}")

    train_df, val_df, test_df = chronological_split(df)

    X_train, y_train = train_df[feature_cols], train_df[TARGET]
    X_val, y_val = val_df[feature_cols], val_df[TARGET]
    X_test, y_test = test_df[feature_cols], test_df[TARGET]

    params = _build_model_params(model_type)

    with mlflow.start_run(run_name=f"transaction_{model_type}") as run:
        logger.info(f"MLflow run ID: {run.info.run_id}")

        mlflow.log_param("model_type", model_type)
        mlflow.log_params(params)
        mlflow.log_param("train_end_date", TRAIN_END_DATE)
        mlflow.log_param("val_end_date", VALIDATION_END_DATE)
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("n_train_samples", len(X_train))
        mlflow.log_param("n_val_samples", len(X_val))
        mlflow.log_param("n_test_samples", len(X_test))

        model = get_model(model_type, params)
        _fit(model, model_type, X_train, y_train, X_val, y_val)

        val_pred = model.predict(X_val)
        for k, v in evaluate_model(y_val.values, val_pred).items():
            mlflow.log_metric(f"val_{k}", v)

        test_pred = model.predict(X_test)
        test_metrics = evaluate_model(y_test.values, test_pred)
        for k, v in test_metrics.items():
            mlflow.log_metric(f"test_{k}", v)

        importance_df = get_feature_importance(model, feature_cols, top_n=len(feature_cols))
        mlflow.log_artifact(plot_feature_importance(importance_df, "feature_importance.png"))
        mlflow.log_artifact(plot_predictions(y_test.values, test_pred, "predictions.png"))

        # Wrap the booster in a pyfunc that re-casts categorical columns on input,
        # so the model survives MLflow's JSON serving round-trip (which strips
        # the `category` dtype). Signature is inferred from the dtypes the
        # serving API will actually send: strings for categoricals (JSON ⇒
        # str), int32 for year/month (MLflow's `integer` is int32), float64
        # for assessed_value.
        example_in = X_train.head(1).astype({
            **{c: "string" for c in CATEGORICAL_FEATURES},
            "list_year": "int32",
            "month_recorded": "int32",
            "assessed_value": "float64",
        })
        wrapped = CategoricalTreeModel(model, CATEGORICAL_FEATURES)
        signature = infer_signature(example_in, model.predict(X_train.head(1)))
        mlflow.pyfunc.log_model(
            artifact_path="model",
            python_model=wrapped,
            signature=signature,
            input_example=example_in,
            code_paths=[str(Path(__file__).parent / "inference.py")],
        )

        if use_cv:
            logger.info(f"Running {TIME_SERIES_CV_SPLITS}-fold TimeSeriesSplit CV")
            full_X = pd.concat([X_train, X_val], axis=0)
            full_y = pd.concat([y_train, y_val], axis=0)
            tscv = TimeSeriesSplit(n_splits=TIME_SERIES_CV_SPLITS)
            cv_scores = []
            for fold, (tr_idx, te_idx) in enumerate(tscv.split(full_X)):
                fold_model = get_model(model_type, params)
                _fit(
                    fold_model, model_type,
                    full_X.iloc[tr_idx], full_y.iloc[tr_idx],
                    full_X.iloc[te_idx], full_y.iloc[te_idx],
                )
                fold_pred = fold_model.predict(full_X.iloc[te_idx])
                fold_mae = evaluate_model(full_y.iloc[te_idx].values, fold_pred)["mae"]
                cv_scores.append(fold_mae)
                mlflow.log_metric("cv_fold_mae", fold_mae, step=fold)
            mlflow.log_metric("cv_mean_mae", float(np.mean(cv_scores)))
            mlflow.log_metric("cv_std_mae", float(np.std(cv_scores)))

        model_uri = f"runs:/{run.info.run_id}/model"
        mv = mlflow.register_model(model_uri, MODEL_NAME)
        logger.info(f"Registered '{MODEL_NAME}' version {mv.version}")

        client = MlflowClient(MLFLOW_TRACKING_URI)
        client.set_registered_model_alias(MODEL_NAME, "staging", mv.version)
        logger.info(f"Set @staging → version {mv.version}")

        return run.info.run_id, test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train property valuation model")
    parser.add_argument("--model-type", default="xgboost", choices=["xgboost", "lightgbm"])
    parser.add_argument("--cv", action="store_true", help="Run time-series CV")
    args = parser.parse_args()

    run_id, metrics = train_baseline(model_type=args.model_type, use_cv=args.cv)
    logger.info(f"Done. Run ID: {run_id}")
    logger.info(
        f"Test MAE: ${metrics['mae']:,.0f} | "
        f"RMSE: ${metrics['rmse']:,.0f} | "
        f"R²: {metrics['r2']:.4f}"
    )
