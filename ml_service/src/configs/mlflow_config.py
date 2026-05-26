"""
MLflow tracking, experiment, and registry configuration.

Environment variables (env_prefix = MLFLOW_):
    MLFLOW_TRACKING_URI          — tracking server URL (required for Docker)
    MLFLOW_EXPERIMENT_NAME       — experiment name
    MLFLOW_MODEL_NAME            — registered model name
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_SQLITE = f"sqlite:///{_PROJECT_ROOT / 'mlflow.db'}"


class MLflowConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="MLFLOW_",
        extra="ignore",
    )

    tracking_uri: str = _DEFAULT_SQLITE
    experiment_name: str = "PropertyValuation"
    tuning_experiment_name: str = "PropertyValuation_Tuning"
    monitoring_experiment_name: str = "Production_Monitoring"
    model_name: str = "PropertyValuationModel"


mlflow_config = MLflowConfig()
