"""
Feature engineering configuration.

Controls lag periods, rolling window sizes, and calendar features
used during the temporal feature pipeline.

Environment variables (env_prefix = FEATURE_):
    FEATURE_LAG_PERIODS       — JSON list, e.g. [1,3,6,12]
    FEATURE_ROLLING_WINDOWS   — JSON list, e.g. [3,6,12]
"""

from typing import List
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class FeatureConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="FEATURE_",
        extra="ignore",
    )

    lag_periods: List[int] = [1, 3, 6, 12]
    rolling_windows: List[int] = [3, 6, 12]
    calendar_features: List[str] = ["year", "month", "quarter", "day_of_week"]
    momentum_periods: List[int] = [1, 3, 12]


feature_config = FeatureConfig()
