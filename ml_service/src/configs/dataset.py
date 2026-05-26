"""
Dataset column mapping and filtering configuration.

Defines the schema of the raw dataset — column names, valid property
types, and temporal split cutoff dates.

Environment variables (env_prefix = DATASET_):
    DATASET_TRAIN_END_DATE        — e.g. 2023-06-30
    DATASET_VALIDATION_END_DATE   — e.g. 2024-03-31
    DATASET_MIN_SALE_PRICE
    DATASET_MAX_SALE_PRICE
"""

from typing import List
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class DatasetConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="DATASET_",
        extra="ignore",
    )

    date_col: str = "Date Recorded"
    target_col: str = "Sale Amount"
    assessed_value_col: str = "Assessed Value"
    property_type_col: str = "Property Type"
    town_col: str = "Town"
    residential_type_col: str = "Residential Type"
    sales_ratio_col: str = "Sales Ratio"

    valid_property_types: List[str] = ["Residential"]

    min_sale_price: float = 1_000
    max_sale_price: float = 10_000_000

    train_end_date: str = "2023-06-30"
    validation_end_date: str = "2024-03-31"


dataset_config = DatasetConfig()
