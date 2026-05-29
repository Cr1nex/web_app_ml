"""
Pydantic request/response schemas for the Property Valuation API.

The model is a per-transaction regressor — each request is one (or many)
real-estate transactions and the response is the predicted sale price(s).
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Transaction schema (matches `src/data/transaction_features.py`)
# ============================================================
class TransactionFeatures(BaseModel):
    """Features describing one real-estate transaction."""

    town: str = Field(..., examples=["Avon"])
    property_type: str = Field("Residential", examples=["Residential"])
    residential_type: str = Field("Single Family", examples=["Single Family"])
    assessed_value: float = Field(..., gt=0, examples=[180000])
    list_year: int = Field(..., ge=1900, le=2100, examples=[2021])
    month_recorded: int = Field(..., ge=1, le=12, examples=[6])


# ============================================================
# Request Models
# ============================================================
class PredictRequest(BaseModel):
    """Single-transaction prediction request."""

    features: TransactionFeatures


class BatchPredictRequest(BaseModel):
    """Batch prediction request — one entry per transaction."""

    instances: List[TransactionFeatures]


# ============================================================
# Response Models
# ============================================================
class PredictResponse(BaseModel):
    predictions: List[float]
    count: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool


class ModelInfoResponse(BaseModel):
    model_name: str
    run_id: Optional[str] = None
    model_uri: Optional[str] = None
