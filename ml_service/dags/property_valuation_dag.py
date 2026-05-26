"""
Airflow DAG: Property Valuation ML Pipeline

Automates the full ML lifecycle:
    1. Feature Engineering — process raw data into feature matrix
    2. Model Training — train baseline XGBoost model with MLflow tracking
    3. Hyperparameter Tuning — search for optimal parameters
    4. Model Registration — register best model to MLflow Registry
    5. Monitoring — run drift detection on production model

Schedule: Weekly (every Monday at 6 AM) to retrain on latest data.

Setup:
    Set AIRFLOW_HOME or copy this file into your Airflow dags/ folder.
    Ensure the project virtualenv is accessible to the Airflow worker.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.features import build_feature_matrix
from src.services.train import train_baseline
from src.services.tune import run_tuning as tune
from src.deployment.monitor import run_monitoring as monitor

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "start_date": datetime(2026, 5, 18),
}


# Task callables
def run_feature_engineering(**kwargs):
    """Execute the feature engineering pipeline."""
    df = build_feature_matrix()
    logger.info(f"Feature matrix built: {df.shape}")
    return df.shape[0]


def run_training(**kwargs):
    """Train the baseline model and log to MLflow."""
    run_id, metrics = train_baseline(model_type="xgboost", use_cv=True)
    logger.info(f"Training complete. Run ID: {run_id}, Test MAE: ${metrics['mae']:,.0f}")
    return {"run_id": run_id, "mae": metrics["mae"]}


def run_tuning(**kwargs):
    """Run hyperparameter optimization."""
    run_id, mae, params = tune(model_type="xgboost", max_evals=20)
    logger.info(f"Tuning complete. Best MAE: ${mae:,.0f}")
    return {"run_id": run_id, "mae": mae}


def run_monitoring(**kwargs):
    """Run production monitoring / drift detection."""
    monitor(n_batches=5, batch_size=20, use_api=False)
    logger.info("Monitoring complete.")


with DAG(
    dag_id="property_valuation_training_pipeline",
    default_args=default_args,
    description="End-to-end ML pipeline: features → train → tune → register",
    schedule_interval="0 6 * * 1",  # Every Monday at 6 AM
    catchup=False,
    tags=["mlops", "property-valuation", "training"],
) as training_dag:

    feature_task = PythonOperator(
        task_id="feature_engineering",
        python_callable=run_feature_engineering,
    )

    train_task = PythonOperator(
        task_id="baseline_training",
        python_callable=run_training,
    )

    tune_task = PythonOperator(
        task_id="hyperparameter_tuning",
        python_callable=run_tuning,
    )

    # Chain: features → training → tuning
    feature_task >> train_task >> tune_task


# DAG Definition: Monitoring Pipeline

with DAG(
    dag_id="property_valuation_monitoring",
    default_args=default_args,
    description="Production model monitoring and drift detection",
    schedule_interval="0 8 * * *",  # Daily at 8 AM
    catchup=False,
    tags=["mlops", "property-valuation", "monitoring"],
) as monitoring_dag:

    monitor_task = PythonOperator(
        task_id="run_monitoring",
        python_callable=run_monitoring,
    )

    # MLflow server health check before monitoring
    health_check = BashOperator(
        task_id="mlflow_health_check",
        bash_command="curl -sf http://localhost:5000/health || echo 'MLflow server not responding'",
    )

    health_check >> monitor_task
