"""
Pydantic request/response schemas for the Property Valuation API.

Used by FastAPI routes for automatic validation and OpenAPI docs.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================
# Request Models
# ============================================================
class PredictRequest(BaseModel):
    """Single prediction request body."""
    features: Dict[str, float] = Field(
        ...,
        example={
            "year": 2020,
            "month": 6,
            "quarter": 2,
            "transaction_count": 45,
            "median_assessed_value": 150000,
            "median_sale_price_lag_1": 250000,
            "median_sale_price_lag_3": 245000,
            "median_sale_price_lag_6": 240000,
            "median_sale_price_lag_12": 230000,
            "median_sale_price_rolling_mean_3": 248000,
            "median_sale_price_rolling_std_3": 5000,
            "median_sale_price_rolling_mean_6": 246000,
            "median_sale_price_rolling_std_6": 6000,
            "median_sale_price_rolling_mean_12": 242000,
            "median_sale_price_rolling_std_12": 7000,
            "price_pct_change_1m": 0.02,
            "price_pct_change_3m": 0.05,
            "price_pct_change_12m": 0.08,
            "median_sales_ratio": 0.92,
        },
    )


class BatchPredictRequest(BaseModel):
    """Batch prediction request body."""
    instances: List[Dict[str, float]]


# ============================================================
# Response Models
# ============================================================
class PredictResponse(BaseModel):
    """Prediction response."""
    predictions: List[float]
    count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool


class ModelInfoResponse(BaseModel):
    """Model metadata response."""
    model_name: str
    run_id: Optional[str] = None
    model_uri: Optional[str] = None
