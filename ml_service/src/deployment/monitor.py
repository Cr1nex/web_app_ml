"""
Production monitoring script for the Property Valuation model.

Simulates new property listings arriving over time, sends them to
the deployed model API, compares predictions against simulated actuals,
and logs drift/performance metrics to a dedicated MLflow experiment.

Usage:
    python -m src.deployment.monitor
    python -m src.deployment.monitor --api-url http://localhost:5002 --n-batches 10
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

import mlflow
import numpy as np
import pandas as pd
import requests
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    MLFLOW_TRACKING_URI,
    MONITORING_EXPERIMENT_NAME,
    PROCESSED_FEATURES_FILE,
    VALIDATION_END_DATE,
    MAE_ALERT_MULTIPLIER,
    DRIFT_SIGNIFICANCE_LEVEL,
)
from src.services.model import evaluate_model
from src.services.train import MONTHLY_TARGET, get_feature_columns

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def load_test_data() -> pd.DataFrame:
    """Load test data (post-validation period) for monitoring simulation."""
    df = pd.read_parquet(PROCESSED_FEATURES_FILE)
    test_df = df[df["date"] > VALIDATION_END_DATE].reset_index(drop=True)
    logger.info(f"Loaded {len(test_df)} test records for monitoring")
    return test_df


def simulate_drift(df: pd.DataFrame, drift_factor: float = 0.0) -> pd.DataFrame:
    """
    Add simulated market drift to test data.

    drift_factor: 0.0 = no drift, 0.1 = 10% shift in feature distributions
    """
    drifted = df.copy()
    numeric_cols = drifted.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        noise = np.random.normal(0, drift_factor * drifted[col].std(), len(drifted))
        drifted[col] = drifted[col] + noise
    return drifted


def detect_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_cols: list,
) -> dict:
    """
    Detect feature drift using Kolmogorov-Smirnov test.

    Returns dict with drift metrics per feature.
    """
    drift_results = {}
    n_drifted = 0

    for col in feature_cols:
        if col in reference_df.columns and col in current_df.columns:
            stat, p_value = stats.ks_2samp(
                reference_df[col].dropna(),
                current_df[col].dropna(),
            )
            is_drifted = p_value < DRIFT_SIGNIFICANCE_LEVEL
            if is_drifted:
                n_drifted += 1
            drift_results[col] = {
                "ks_statistic": float(stat),
                "p_value": float(p_value),
                "drifted": is_drifted,
            }

    return {
        "feature_drift": drift_results,
        "n_drifted_features": n_drifted,
        "drift_ratio": n_drifted / len(feature_cols) if feature_cols else 0,
    }


def send_prediction_request(api_url: str, features: dict) -> float:
    """Send a prediction request to the model API."""
    response = requests.post(
        f"{api_url}/predict",
        json={"features": features},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["predictions"][0]


def run_monitoring(
    api_url: str = "http://localhost:5002",
    n_batches: int = 10,
    batch_size: int = 20,
    drift_increment: float = 0.02,
    use_api: bool = True,
):
    """
    Run production monitoring simulation.

    Simulates n_batches of new data arriving over time, with
    increasing drift. Logs metrics to MLflow.
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MONITORING_EXPERIMENT_NAME)

    # Load reference (training) data and test data
    full_df = pd.read_parquet(PROCESSED_FEATURES_FILE)
    reference_df = full_df[full_df["date"] <= VALIDATION_END_DATE]
    test_df = load_test_data()
    feature_cols = get_feature_columns(full_df)

    # Calculate baseline MAE from training period
    baseline_mae = None

    with mlflow.start_run(run_name=f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        mlflow.log_param("n_batches", n_batches)
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_param("drift_increment", drift_increment)
        mlflow.log_param("api_url", api_url)

        for batch_idx in range(n_batches):
            logger.info(f"--- Batch {batch_idx + 1}/{n_batches} ---")

            # Sample a batch from test data with increasing drift
            drift_factor = drift_increment * batch_idx
            batch = test_df.sample(n=min(batch_size, len(test_df)), random_state=batch_idx)
            batch_drifted = simulate_drift(batch, drift_factor)

            # Get predictions
            actuals = batch[MONTHLY_TARGET].values
            if use_api:
                try:
                    predictions = []
                    for _, row in batch_drifted[feature_cols].iterrows():
                        pred = send_prediction_request(api_url, row.to_dict())
                        predictions.append(pred)
                    predictions = np.array(predictions)
                except Exception as e:
                    logger.warning(f"API call failed: {e}. Using direct model inference.")
                    use_api = False

            if not use_api:
                # Direct inference fallback (load model from registry)
                model = mlflow.pyfunc.load_model(f"models:/PropertyValuationModel@champion")
                predictions = model.predict(batch_drifted[feature_cols])

            # Calculate metrics
            metrics = evaluate_model(actuals, predictions)

            # Set baseline from first batch
            if baseline_mae is None:
                baseline_mae = metrics["mae"]
                mlflow.log_metric("baseline_mae", baseline_mae)

            # Log metrics with batch step
            mlflow.log_metric("batch_mae", metrics["mae"], step=batch_idx)
            mlflow.log_metric("batch_rmse", metrics["rmse"], step=batch_idx)
            mlflow.log_metric("batch_mape", metrics["mape"], step=batch_idx)
            mlflow.log_metric("batch_r2", metrics["r2"], step=batch_idx)
            mlflow.log_metric("drift_factor", drift_factor, step=batch_idx)

            # Feature drift detection
            drift_info = detect_feature_drift(reference_df, batch_drifted, feature_cols)
            mlflow.log_metric("n_drifted_features", drift_info["n_drifted_features"], step=batch_idx)
            mlflow.log_metric("drift_ratio", drift_info["drift_ratio"], step=batch_idx)

            # Alert check
            if metrics["mae"] > baseline_mae * MAE_ALERT_MULTIPLIER:
                logger.warning(
                    f"⚠ ALERT: MAE ${metrics['mae']:,.0f} exceeds "
                    f"{MAE_ALERT_MULTIPLIER}× baseline (${baseline_mae * MAE_ALERT_MULTIPLIER:,.0f})"
                )
                mlflow.log_metric("alert_triggered", 1, step=batch_idx)
            else:
                mlflow.log_metric("alert_triggered", 0, step=batch_idx)

            time.sleep(0.5)  # Simulate time passing between batches

        logger.info("Monitoring complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Production monitoring")
    parser.add_argument("--api-url", default="http://localhost:5002")
    parser.add_argument("--n-batches", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--no-api", action="store_true", help="Use direct model loading instead of API")
    args = parser.parse_args()

    run_monitoring(
        api_url=args.api_url,
        n_batches=args.n_batches,
        batch_size=args.batch_size,
        use_api=not args.no_api,
    )
