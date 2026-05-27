"""
API v1 route handlers for property valuation predictions.

Endpoints:
    GET  /api/v1/health         — Health check
    POST /api/v1/predict        — Single prediction
    POST /api/v1/predict/batch  — Batch predictions
    GET  /api/v1/model-info     — Model metadata
    POST /api/v1/reload         — Hot-reload model from MLflow Registry
"""

import logging
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

import src.api.v1.app as app_module
from src.api.v1.deps import get_current_user_id
from src.config import MODEL_NAME
from src.configs.models.api_models import (
    PredictRequest,
    BatchPredictRequest,
    PredictResponse,
    HealthResponse,
    ModelInfoResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Route Handlers

@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check — confirms the API is running and model is loaded."""
    return HealthResponse(status="healthy", model_loaded=app_module.model is not None)


@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: PredictRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Predict property valuation from a single set of features."""
    if app_module.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        input_df = pd.DataFrame([request.features])
        predictions = app_module.model.predict(input_df)

        return PredictResponse(
            predictions=predictions.tolist(),
            count=len(predictions),
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/batch", response_model=PredictResponse)
async def predict_batch(
    request: BatchPredictRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Batch predict property valuations from a list of feature dicts."""
    if app_module.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        input_df = pd.DataFrame(request.instances)
        predictions = app_module.model.predict(input_df)

        return PredictResponse(
            predictions=predictions.tolist(),
            count=len(predictions),
        )
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
