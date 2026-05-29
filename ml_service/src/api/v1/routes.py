"""
API v1 route handlers for the property valuation API.

Endpoints:
    GET  /api/v1/health         — Health check
    POST /api/v1/predict        — Single-transaction prediction
    POST /api/v1/predict/batch  — Batch predictions
    GET  /api/v1/model-info     — Model metadata
    POST /api/v1/reload         — Hot-reload model from MLflow Registry
"""

import logging
from typing import List
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

import src.api.v1.app as app_module
from src.api.v1.deps import get_current_user_id
from src.config import MODEL_NAME
from src.configs.models.api_models import (
    BatchPredictRequest,
    HealthResponse,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    TransactionFeatures,
)
from src.data.transaction_features import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_dataframe(transactions: List[TransactionFeatures]) -> pd.DataFrame:
    """Convert request models into the column order + dtypes the model expects.

    The pyfunc wrapper (CategoricalTreeModel) re-applies `category` dtype on
    its side, so we send plain strings here to match the logged signature.
    Integer columns are cast to int32 because MLflow's `integer` schema type
    means int32 specifically, and pandas otherwise builds int64 from JSON
    which the schema enforcer refuses to downcast implicitly.
    """
    df = pd.DataFrame([t.model_dump() for t in transactions])
    df = df[FEATURE_COLUMNS]
    df["list_year"] = df["list_year"].astype("int32")
    df["month_recorded"] = df["month_recorded"].astype("int32")
    df["assessed_value"] = df["assessed_value"].astype("float64")
    return df


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check — confirms the API is running and model is loaded."""
    return HealthResponse(status="healthy", model_loaded=app_module.model is not None)


@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: PredictRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Predict the sale price of a single transaction."""
    if app_module.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        input_df = _to_dataframe([request.features])
        predictions = app_module.model.predict(input_df)
        return PredictResponse(predictions=predictions.tolist(), count=len(predictions))
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/batch", response_model=PredictResponse)
async def predict_batch(
    request: BatchPredictRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Predict sale prices for a batch of transactions."""
    if app_module.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        input_df = _to_dataframe(request.instances)
        predictions = app_module.model.predict(input_df)
        return PredictResponse(predictions=predictions.tolist(), count=len(predictions))
    except Exception as e:
        logger.error(f"Batch prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info", response_model=ModelInfoResponse)
async def model_info():
    """Return metadata about the currently loaded model."""
    if app_module.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    metadata = app_module.model.metadata
    return ModelInfoResponse(
        model_name=MODEL_NAME,
        run_id=getattr(metadata, "run_id", None),
        model_uri=str(getattr(metadata, "model_uri", None)),
    )


@router.post("/reload")
async def reload_model():
    """
    Hot-reload the model from MLflow Registry without restarting the container.

    Call this after promoting a new champion on the MLflow server:
        python -m src.services.registry promote --version N
        curl -X POST http://<host>:5002/api/v1/reload
    """
    try:
        app_module.load_production_model()
        metadata = app_module.model.metadata
        return {
            "status": "reloaded",
            "run_id": getattr(metadata, "run_id", None),
            "model_uri": str(getattr(metadata, "model_uri", None)),
        }
    except Exception as e:
        logger.error(f"Reload failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
