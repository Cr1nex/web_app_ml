from typing import Dict, List

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    features: Dict[str, float] = Field(..., description="Feature name → value")


class BatchPredictRequest(BaseModel):
    instances: List[Dict[str, float]]


class PredictResponse(BaseModel):
    predictions: List[float]
    count: int
