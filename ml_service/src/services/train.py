"""
Core training script with MLflow experiment tracking.

Implements chronological train/test splitting (no random shuffle)
and logs parameters, metrics, model artifacts, and feature importance
to MLflow for the baseline XGBoost property valuation model.

Usage:
    python -m src.services.train
    python -m src.services.train --model-type lightgbm
    python -m src.services.train --cv
"""

import argparse
import logging
import sys
from pathlib import Path

import mlflow
import mlflow.xgboost
import mlflow.lightgbm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.model_selection import TimeSeriesSplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    MLFLOW_TRACKING_URI,
    EXPERIMENT_NAME,
    PROCESSED_FEATURES_FILE,
    TRAIN_END_DATE,
    VALIDATION_END_DATE,
    TARGET_COL,
    TOWN_COL,
    MODEL_NAME,
    TIME_SERIES_CV_SPLITS,
    DEFAULT_XGBOOST_PARAMS,
    DEFAULT_LIGHTGBM_PARAMS,
)
from src.services.model import get_model, evaluate_model, get_feature_importance
from src.data.features import build_feature_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# Target for the monthly aggregated data
MONTHLY_TARGET = "median_sale_price"


def load_features() -> pd.DataFrame:
    """Load processed feature matrix, building it if it doesn't exist."""
    if not PROCESSED_FEATURES_FILE.exists():
        logger.info("Processed features not found. Running feature pipeline...")
        return build_feature_matrix()
    logger.info(f"Loading features from {PROCESSED_FEATURES_FILE}")
    return pd.read_parquet(PROCESSED_FEATURES_FILE)


def get_feature_columns(df: pd.DataFrame) -> list:
    """Return list of feature columns (exclude target, date, identifiers)."""
    exclude = {MONTHLY_TARGET, "mean_sale_price", "date", TOWN_COL, "year_month"}
    return [c for c in df.columns if c not in exclude]


def chronological_split(df: pd.DataFrame):
    """
    Split data chronologically to prevent temporal leakage.

    Train:      dates <= TRAIN_END_DATE
    Validation: TRAIN_END_DATE < dates <= VALIDATION_END_DATE
    Test:       dates > VALIDATION_END_DATE
    """
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])

    train_cutoff = pd.Timestamp(TRAIN_END_DATE)
    val_cutoff = pd.Timestamp(VALIDATION_END_DATE)

    logger.info(f"Date range in data: {df['date'].min()} — {df['date'].max()}")
    logger.info(f"Split cutoffs: train <= {train_cutoff}, val <= {val_cutoff}")

    train_mask = df["date"] <= train_cutoff
    val_mask = (df["date"] > train_cutoff) & (df["date"] <= val_cutoff)
    test_mask = df["date"] > val_cutoff

    train_df = df[train_mask]
    val_df = df[val_mask]
    test_df = df[test_mask]

    logger.info(f"Chronological split — Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

    if len(train_df) == 0 or len(val_df) == 0 or len(test_df) == 0:
        raise ValueError(
            f"Empty split detected! Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}. "
            f"Check TRAIN_END_DATE={TRAIN_END_DATE} and VALIDATION_END_DATE={VALIDATION_END_DATE} "
            f"against data range {df['date'].min()} — {df['date'].max()}"
        )

    return train_df, val_df, test_df


def plot_feature_importance(importance_df: pd.DataFrame, output_path: str) -> str:
    """Create and save a feature importance bar chart."""
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(importance_df["feature"], importance_df["importance"], color="#2196F3")
    ax.set_xlabel("Importance")
    ax.set_title("Top Feature Importances")
    ax.invert_yaxis()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def plot_predictions(y_true, y_pred, output_path: str) -> str:
    """Create actual vs predicted scatter plot."""
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(y_true, y_pred, alpha=0.3, s=10, color="#4CAF50")
    lims = [min(y_true.min(), y_pred.min()), max(y_true.max(), y_pred.max())]
    ax.plot(lims, lims, "r--", linewidth=1, label="Perfect prediction")
    ax.set_xlabel("Actual Price ($)")
    ax.set_ylabel("Predicted Price ($)")
    ax.set_title("Actual vs Predicted Sale Prices")
    ax.legend()
    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def train_baseline(model_type: str = "xgboost", use_cv: bool = False):
    """
    Train a baseline model and log everything to MLflow.

    Args:
        model_type: "xgboost" or "lightgbm"
        use_cv: If True, also run TimeSeriesSplit cross-validation
    """
    # ── Setup MLflow ──
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    # ── Load data ──
    df = load_features()
    feature_cols = get_feature_columns(df)
    logger.info(f"Using {len(feature_cols)} features: {feature_cols}")

    # ── Chronological split ──
    train_df, val_df, test_df = chronological_split(df)

    X_train = train_df[feature_cols]
    y_train = train_df[MONTHLY_TARGET]
    X_val = val_df[feature_cols]
    y_val = val_df[MONTHLY_TARGET]
    X_test = test_df[feature_cols]
    y_test = test_df[MONTHLY_TARGET]

    # ── Get model params ──
    if model_type == "xgboost":
        params = DEFAULT_XGBOOST_PARAMS.copy()
    else:
        params = DEFAULT_LIGHTGBM_PARAMS.copy()

    # ── MLflow Run ──
    with mlflow.start_run(run_name=f"baseline_{model_type}") as run:
        logger.info(f"MLflow Run ID: {run.info.run_id}")

        # Log parameters
        mlflow.log_param("model_type", model_type)
        mlflow.log_params(params)
        mlflow.log_param("train_end_date", TRAIN_END_DATE)
        mlflow.log_param("val_end_date", VALIDATION_END_DATE)
        mlflow.log_param("n_features", len(feature_cols))
        mlflow.log_param("n_train_samples", len(X_train))
        mlflow.log_param("n_val_samples", len(X_val))
        mlflow.log_param("n_test_samples", len(X_test))

        # Train model
        model = get_model(model_type, params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        # Evaluate on validation set
        val_pred = model.predict(X_val)
        val_metrics = evaluate_model(y_val.values, val_pred)
        for key, value in val_metrics.items():
            mlflow.log_metric(f"val_{key}", value)

        # Evaluate on test set
        test_pred = model.predict(X_test)
        test_metrics = evaluate_model(y_test.values, test_pred)
        for key, value in test_metrics.items():
            mlflow.log_metric(f"test_{key}", value)

        # Log feature importance
        importance_df = get_feature_importance(model, feature_cols)
        fi_path = plot_feature_importance(importance_df, "feature_importance.png")
        mlflow.log_artifact(fi_path)

        # Log predictions plot
        pred_path = plot_predictions(y_test.values, test_pred, "predictions.png")
        mlflow.log_artifact(pred_path)

        # Log model with signature
        signature = infer_signature(X_train, model.predict(X_train))
        if model_type == "xgboost":
            mlflow.xgboost.log_model(
                model, "model",
                signature=signature,
                input_example=X_train.head(1),
            )
        else:
            mlflow.lightgbm.log_model(
                model, "model",
                signature=signature,
                input_example=X_train.head(1),
            )

        # ── Optional: Time-Series Cross-Validation ──
        if use_cv:
            logger.info(f"Running {TIME_SERIES_CV_SPLITS}-fold TimeSeriesSplit CV")
            full_X = pd.concat([X_train, X_val], axis=0)
            full_y = pd.concat([y_train, y_val], axis=0)

            tscv = TimeSeriesSplit(n_splits=TIME_SERIES_CV_SPLITS)
            cv_scores = []

            for fold, (tr_idx, te_idx) in enumerate(tscv.split(full_X)):
                fold_model = get_model(model_type, params)
                fold_model.fit(full_X.iloc[tr_idx], full_y.iloc[tr_idx], verbose=False)
                fold_pred = fold_model.predict(full_X.iloc[te_idx])
                fold_metrics = evaluate_model(full_y.iloc[te_idx].values, fold_pred)
                cv_scores.append(fold_metrics["mae"])
                mlflow.log_metric("cv_fold_mae", fold_metrics["mae"], step=fold)

            mlflow.log_metric("cv_mean_mae", float(np.mean(cv_scores)))
            mlflow.log_metric("cv_std_mae", float(np.std(cv_scores)))
            logger.info(f"CV MAE: {np.mean(cv_scores):,.0f} ± {np.std(cv_scores):,.0f}")

        # ── Register model in Model Registry ──
        model_uri = f"runs:/{run.info.run_id}/model"
        mv = mlflow.register_model(model_uri, MODEL_NAME)
        logger.info(f"Registered model '{MODEL_NAME}' version {mv.version}")

        # Set staging alias for the baseline
        client = MlflowClient(MLFLOW_TRACKING_URI)
        client.set_registered_model_alias(MODEL_NAME, "staging", mv.version)
        logger.info(f"Set alias @staging → version {mv.version}")

        logger.info(f"Run completed. View at: mlflow ui --backend-store-uri {MLFLOW_TRACKING_URI}")
        return run.info.run_id, test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train property valuation model")
    parser.add_argument("--model-type", default="xgboost", choices=["xgboost", "lightgbm"])
    parser.add_argument("--cv", action="store_true", help="Run time-series cross-validation")
    args = parser.parse_args()

    run_id, metrics = train_baseline(model_type=args.model_type, use_cv=args.cv)
    logger.info(f"Training complete. Run ID: {run_id}")
    logger.info(f"Test MAE: ${metrics['mae']:,.0f} | Test RMSE: ${metrics['rmse']:,.0f} | Test R²: {metrics['r2']:.4f}")
