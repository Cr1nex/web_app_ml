from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    """One transaction. Categoricals are strings, numerics are floats — the
    ml_service validates the exact shape."""

    features: Dict[str, Any] = Field(..., description="Transaction field → value")


class BatchPredictRequest(BaseModel):
    instances: List[Dict[str, Any]]


class PredictResponse(BaseModel):
    predictions: List[float]
    count: int
