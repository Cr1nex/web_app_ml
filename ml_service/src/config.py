"""
Backward-compatible re-export layer.

All configuration is now defined as Pydantic models in src/configs/.
This module re-exports flat variables so existing imports continue to work.

Prefer importing directly from src.configs.* in new code.
"""

from src.configs.paths import path_config
from src.configs.dataset import dataset_config
from src.configs.features import feature_config
from src.configs.mlflow_config import mlflow_config
from src.configs.training import training_config
from src.configs.monitoring import monitoring_config
from src.configs.models.xgboost_config import xgboost_config
from src.configs.models.lightgbm_config import lightgbm_config

# ── Paths ──
PROJECT_ROOT = path_config.project_root
DATA_DIR = path_config.data_dir
RAW_DATA_DIR = path_config.raw_data_dir
PROCESSED_DATA_DIR = path_config.processed_data_dir
ARTIFACTS_DIR = path_config.artifacts_dir
PROCESSED_FEATURES_FILE = path_config.processed_features_filepath

try:
    RAW_DATA_FILE = path_config.raw_data_filepath
except FileNotFoundError:
    RAW_DATA_FILE = RAW_DATA_DIR / "Real_Estate_Sales.csv"  # placeholder

# ── Dataset ──
DATE_COL = dataset_config.date_col
TARGET_COL = dataset_config.target_col
ASSESSED_VALUE_COL = dataset_config.assessed_value_col
PROPERTY_TYPE_COL = dataset_config.property_type_col
TOWN_COL = dataset_config.town_col
RESIDENTIAL_TYPE_COL = dataset_config.residential_type_col
SALES_RATIO_COL = dataset_config.sales_ratio_col
VALID_PROPERTY_TYPES = dataset_config.valid_property_types
TRAIN_END_DATE = dataset_config.train_end_date
VALIDATION_END_DATE = dataset_config.validation_end_date

# ── Features ──
LAG_PERIODS = feature_config.lag_periods
ROLLING_WINDOWS = feature_config.rolling_windows
CALENDAR_FEATURES = feature_config.calendar_features

# ── MLflow ──
MLFLOW_TRACKING_URI = mlflow_config.tracking_uri
EXPERIMENT_NAME = mlflow_config.experiment_name
TUNING_EXPERIMENT_NAME = mlflow_config.tuning_experiment_name
MONITORING_EXPERIMENT_NAME = mlflow_config.monitoring_experiment_name
MODEL_NAME = mlflow_config.model_name

# ── Model hyperparameters ──
DEFAULT_XGBOOST_PARAMS = xgboost_config.to_dict()
DEFAULT_LIGHTGBM_PARAMS = lightgbm_config.to_dict()

# ── Training ──
TIME_SERIES_CV_SPLITS = training_config.time_series_cv_splits
RANDOM_STATE = training_config.random_state

# ── Monitoring ──
MAE_ALERT_MULTIPLIER = monitoring_config.mae_alert_multiplier
DRIFT_SIGNIFICANCE_LEVEL = monitoring_config.drift_significance_level
