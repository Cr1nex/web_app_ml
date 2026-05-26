"""
Training pipeline configuration.

Environment variables (env_prefix = TRAINING_):
    TRAINING_TIME_SERIES_CV_SPLITS
    TRAINING_RANDOM_STATE
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TrainingConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="TRAINING_",
        extra="ignore",
    )

    time_series_cv_splits: int = 5
    random_state: int = 42


training_config = TrainingConfig()
