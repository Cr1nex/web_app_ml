from uuid import UUID

from fastapi import APIRouter, Depends, Request

from api.routers.v1.prediction.schemas import (
    BatchPredictRequest,
    PredictRequest,
    PredictResponse,
)
from core.configs.settings import settings
from core.rate_limit import limiter
from core.utils.deps import get_current_user_id
from services.prediction_service import PredictionService

router = APIRouter(prefix="/prediction", tags=["prediction"])


def get_prediction_service(request: Request) -> PredictionService:
    return PredictionService(
        http_client=request.app.state.http_client,
        base_url=settings.ml_service_url,
    )


@router.post("/predict", response_model=PredictResponse)
@limiter.limit("60/minute")
async def predict(
    request: Request,
    payload: PredictRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: PredictionService = Depends(get_prediction_service),
):
    return await service.predict(payload.features, request)


@router.post("/predict/batch", response_model=PredictResponse)
@limiter.limit("60/minute")
async def predict_batch(
    request: Request,
    payload: BatchPredictRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: PredictionService = Depends(get_prediction_service),
):
    return await service.predict_batch(payload.instances, request)
