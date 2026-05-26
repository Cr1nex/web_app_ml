"""
LightGBM hyperparameter configuration.

Environment variables (env_prefix = LGBM_):
    LGBM_N_ESTIMATORS, LGBM_MAX_DEPTH, LGBM_LEARNING_RATE, ...
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class LightGBMConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="LGBM_",
        extra="ignore",
    )

    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    subsample: float = Field(0.8, ge=0.0, le=1.0)
    colsample_bytree: float = Field(0.8, ge=0.0, le=1.0)
    min_child_samples: int = 20
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    random_state: int = 42
    n_jobs: int = -1
    verbose: int = -1

    def to_dict(self) -> dict:
        return self.model_dump()


lightgbm_config = LightGBMConfig()
