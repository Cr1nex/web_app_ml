"""
Production monitoring thresholds and alerting configuration.

Environment variables (env_prefix = MONITORING_):
    MONITORING_MAE_ALERT_MULTIPLIER
    MONITORING_DRIFT_SIGNIFICANCE_LEVEL
    MONITORING_DEFAULT_N_BATCHES
    MONITORING_DEFAULT_BATCH_SIZE
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class MonitoringConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="MONITORING_",
        extra="ignore",
    )

    mae_alert_multiplier: float = 1.5
    drift_significance_level: float = 0.05
    default_n_batches: int = 10
    default_batch_size: int = 20
    drift_increment: float = 0.02


monitoring_config = MonitoringConfig()
