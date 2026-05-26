"""
Hyperparameter optimization using Hyperopt with MLflow nested runs.

Searches over XGBoost/LightGBM parameters and feature engineering
configs (lag windows, rolling windows) to find the best model.

Usage:
    python -m src.services.tune --max-evals 20
    python -m src.services.tune --max-evals 10 --model-type lightgbm
"""

import argparse
import logging
import sys
from pathlib import Path

import mlflow
import mlflow.xgboost
import mlflow.lightgbm
import numpy as np
import pandas as pd
from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
from mlflow.models import infer_signature
from mlflow import MlflowClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    MLFLOW_TRACKING_URI,
    TUNING_EXPERIMENT_NAME,
    MODEL_NAME,
    PROCESSED_FEATURES_FILE,
    TRAIN_END_DATE,
    VALIDATION_END_DATE,
)
from src.services.model import get_model, evaluate_model
from src.services.train import load_features, get_feature_columns, chronological_split, MONTHLY_TARGET

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# Search Space
# ============================================================
XGBOOST_SPACE = {
    "max_depth": hp.choice("max_depth", [3, 5, 7, 9, 11]),
    "learning_rate": hp.loguniform("learning_rate", np.log(0.01), np.log(0.3)),
    "n_estimators": hp.choice("n_estimators", [100, 200, 300, 500]),
    "subsample": hp.uniform("subsample", 0.6, 1.0),
    "colsample_bytree": hp.uniform("colsample_bytree", 0.6, 1.0),
    "min_child_weight": hp.choice("min_child_weight", [1, 3, 5, 7]),
    "reg_alpha": hp.loguniform("reg_alpha", np.log(0.001), np.log(1.0)),
    "reg_lambda": hp.loguniform("reg_lambda", np.log(0.1), np.log(10.0)),
}

LIGHTGBM_SPACE = {
    "max_depth": hp.choice("max_depth", [3, 5, 7, 9, -1]),
    "learning_rate": hp.loguniform("learning_rate", np.log(0.01), np.log(0.3)),
    "n_estimators": hp.choice("n_estimators", [100, 200, 300, 500]),
    "subsample": hp.uniform("subsample", 0.6, 1.0),
    "colsample_bytree": hp.uniform("colsample_bytree", 0.6, 1.0),
    "min_child_samples": hp.choice("min_child_samples", [5, 10, 20, 30]),
    "reg_alpha": hp.loguniform("reg_alpha", np.log(0.001), np.log(1.0)),
    "reg_lambda": hp.loguniform("reg_lambda", np.log(0.1), np.log(10.0)),
}


def run_tuning(model_type: str = "xgboost", max_evals: int = 20):
    """
    Run hyperparameter optimization with nested MLflow runs.

    Each trial is logged as a child run under one parent run.
    The best model is registered in the MLflow Model Registry.
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(TUNING_EXPERIMENT_NAME)

    # Load data once
    df = load_features()
    feature_cols = get_feature_columns(df)
    train_df, val_df, test_df = chronological_split(df)

    X_train = train_df[feature_cols]
    y_train = train_df[MONTHLY_TARGET]
    X_val = val_df[feature_cols]
    y_val = val_df[MONTHLY_TARGET]
    X_test = test_df[feature_cols]
    y_test = test_df[MONTHLY_TARGET]

    search_space = XGBOOST_SPACE if model_type == "xgboost" else LIGHTGBM_SPACE
    best_run_id = None
    best_mae = float("inf")

    def objective(params):
        nonlocal best_run_id, best_mae

        # Clean params for model constructor
        clean_params = {k: v for k, v in params.items()}
        clean_params["random_state"] = 42
        clean_params["n_jobs"] = -1
        if model_type == "lightgbm":
            clean_params["verbose"] = -1

        with mlflow.start_run(nested=True) as child_run:
            mlflow.log_param("model_type", model_type)
            mlflow.log_params({k: str(v) for k, v in clean_params.items()})

            model = get_model(model_type, clean_params)
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

            # Validation metrics
            val_pred = model.predict(X_val)
            val_metrics = evaluate_model(y_val.values, val_pred)
            for k, v in val_metrics.items():
                mlflow.log_metric(f"val_{k}", v)

            # Test metrics
            test_pred = model.predict(X_test)
            test_metrics = evaluate_model(y_test.values, test_pred)
            for k, v in test_metrics.items():
                mlflow.log_metric(f"test_{k}", v)

            # Log model
            signature = infer_signature(X_train, model.predict(X_train))
            log_fn = mlflow.xgboost.log_model if model_type == "xgboost" else mlflow.lightgbm.log_model
            log_fn(model, "model", signature=signature, input_example=X_train.head(1))

            # Track best
            if val_metrics["mae"] < best_mae:
                best_mae = val_metrics["mae"]
                best_run_id = child_run.info.run_id
                logger.info(f"New best MAE: ${best_mae:,.0f} (run {best_run_id})")

            return {"loss": val_metrics["mae"], "status": STATUS_OK}

    # Parent run
    with mlflow.start_run(run_name=f"tuning_{model_type}_{max_evals}evals") as parent_run:
        mlflow.set_tag("tuning_session", "true")
        mlflow.log_param("model_type", model_type)
        mlflow.log_param("max_evals", max_evals)

        trials = Trials()
        best_params = fmin(
            fn=objective,
            space=search_space,
            algo=tpe.suggest,
            max_evals=max_evals,
            trials=trials,
        )

        mlflow.log_params({f"best_{k}": str(v) for k, v in best_params.items()})
        mlflow.log_metric("best_val_mae", best_mae)

        logger.info(f"Tuning complete. Best MAE: ${best_mae:,.0f}")
        logger.info(f"Best params: {best_params}")

    # Register the best model
    if best_run_id:
        logger.info(f"Registering best model from run {best_run_id}")
        model_uri = f"runs:/{best_run_id}/model"
        mv = mlflow.register_model(model_uri, MODEL_NAME)

        client = MlflowClient(MLFLOW_TRACKING_URI)
        client.set_registered_model_alias(MODEL_NAME, "staging", mv.version)
        logger.info(f"Model {MODEL_NAME} v{mv.version} registered with alias 'staging'")

    return best_run_id, best_mae, best_params


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperparameter tuning")
    parser.add_argument("--max-evals", type=int, default=20)
    parser.add_argument("--model-type", default="xgboost", choices=["xgboost", "lightgbm"])
    args = parser.parse_args()

    run_id, mae, params = run_tuning(model_type=args.model_type, max_evals=args.max_evals)
    logger.info(f"Tuning complete. Best run: {run_id} | Best MAE: ${mae:,.0f}")
    logger.info(f"Best params: {params}")
