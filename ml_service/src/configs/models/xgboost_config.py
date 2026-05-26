"""
XGBoost hyperparameter configuration.

Environment variables (env_prefix = XGBOOST_):
    XGBOOST_N_ESTIMATORS, XGBOOST_MAX_DEPTH, XGBOOST_LEARNING_RATE, ...
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class XGBoostConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="XGBOOST_",
        extra="ignore",
    )

    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.1
    subsample: float = Field(0.8, ge=0.0, le=1.0)
    colsample_bytree: float = Field(0.8, ge=0.0, le=1.0)
    min_child_weight: int = 3
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    random_state: int = 42
    n_jobs: int = -1

    def to_dict(self) -> dict:
        return self.model_dump()


xgboost_config = XGBoostConfig()
