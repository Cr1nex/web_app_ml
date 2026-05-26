"""
Model definitions and evaluation utilities for property valuation.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Any

import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from src.config import DEFAULT_XGBOOST_PARAMS, DEFAULT_LIGHTGBM_PARAMS

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)


def get_xgboost_model(params: Optional[Dict[str, Any]] = None) -> xgb.XGBRegressor:
    """Create a configured XGBoost regressor with defaults from config."""
    model_params = DEFAULT_XGBOOST_PARAMS.copy()
    if params:
        model_params.update(params)
    logger.info(f"Creating XGBoost model with params: {model_params}")
    return xgb.XGBRegressor(**model_params)


def get_lightgbm_model(params: Optional[Dict[str, Any]] = None) -> lgb.LGBMRegressor:
    """Create a configured LightGBM regressor with defaults from config."""
    model_params = DEFAULT_LIGHTGBM_PARAMS.copy()
    if params:
        model_params.update(params)
    logger.info(f"Creating LightGBM model with params: {model_params}")
    return lgb.LGBMRegressor(**model_params)


def get_model(model_type: str = "xgboost", params: Optional[Dict[str, Any]] = None):
    """Model factory — returns 'xgboost' or 'lightgbm' model."""
    factories = {
        "xgboost": get_xgboost_model,
        "lightgbm": get_lightgbm_model,
    }
    if model_type not in factories:
        raise ValueError(f"Unknown model type '{model_type}'. Choose from: {list(factories.keys())}")
    return factories[model_type](params)


def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Compute regression metrics: MAE, RMSE, MAPE, R², Median AE.
    """
    metrics = {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "median_ae": float(np.median(np.abs(y_true - y_pred))),
    }
    logger.info(f"Metrics: MAE=${metrics['mae']:,.0f} | RMSE=${metrics['rmse']:,.0f} | "
                f"MAPE={metrics['mape']:.2%} | R²={metrics['r2']:.4f}")
    return metrics


def get_feature_importance(model, feature_names: list, top_n: int = 20) -> pd.DataFrame:
    """Extract and sort feature importance from a tree-based model."""
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        raise AttributeError("Model does not have feature_importances_ attribute")
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances,
    }).sort_values("importance", ascending=False)
    return importance_df.head(top_n).reset_index(drop=True)
