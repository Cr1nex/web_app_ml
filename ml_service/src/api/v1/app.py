"""
FastAPI application for the Property Valuation API.

Sets up the app, loads the ML model from MLflow Registry on startup,
and includes versioned route routers.

Usage:
    uvicorn src.api.v1.app:app --port 5002 --reload
    python -m src.api.v1.app --port 5002

Model loading priority:
    1. MLFLOW_TRACKING_URI env var (must point to the shared MLflow server)
    2. Alias @champion → @staging → latest registered version
    After promoting a new champion, POST /api/v1/reload to hot-swap the model.
"""

import argparse
import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

import mlflow
import mlflow.pyfunc
import uvicorn
from fastapi import FastAPI
from mlflow import MlflowClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from src.config import MLFLOW_TRACKING_URI, MODEL_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

# Global model reference (loaded once at startup, reloaded via POST /api/v1/reload)
model = None


def load_production_model():
    """
    Load the production model from the shared MLflow Registry.

    Tries @champion → @staging → latest version.
    Raises RuntimeError if no model can be loaded so the caller knows the state.
    """
    global model
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    logger.info(f"Connecting to MLflow at: {MLFLOW_TRACKING_URI}")

    # Try alias-based loading first (MLflow 2.x recommended)
    for alias in ["champion", "staging"]:
        try:
            model_uri = f"models:/{MODEL_NAME}@{alias}"
            model = mlflow.pyfunc.load_model(model_uri)
            logger.info(f"Loaded model from: {model_uri}")
            return
        except Exception as e:
            logger.warning(f"Could not load alias @{alias}: {e}")

    # Fallback: load latest registered version
    try:
        client = MlflowClient(MLFLOW_TRACKING_URI)
        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    except Exception as e:
        raise RuntimeError(
            f"Cannot reach MLflow at '{MLFLOW_TRACKING_URI}'. "
            f"Set MLFLOW_TRACKING_URI to the shared server URL. Error: {e}"
        ) from e

    if not versions:
        raise RuntimeError(
            f"No registered versions found for model '{MODEL_NAME}'. "
            f"Train and register a model first: python -m src.services.train"
        )

    latest = max(versions, key=lambda v: int(v.version))
    model_uri = f"models:/{MODEL_NAME}/{latest.version}"
    model = mlflow.pyfunc.load_model(model_uri)
    logger.info(f"Loaded model from: {model_uri}")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Load model on startup, cleanup on shutdown."""
    try:
        load_production_model()
        logger.info("Model loaded — API ready")
    except Exception as e:
        logger.error(
            f"Model failed to load: {e}\n"
            f"  → Set MLFLOW_TRACKING_URI to your shared MLflow server.\n"
            f"  → Train a model locally and push to that server, then promote to @champion.\n"
            f"  → API is running in degraded mode — predictions will return 503."
        )
    yield
    logger.info("Shutting down API")


app = FastAPI(
    title="Property Valuation API",
    description="Real-time property price forecasting powered by MLflow",
    version="1.0.0",
    lifespan=lifespan,
)

# Register v1 routes
from src.api.v1.routes import router as v1_router
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Property Valuation API")
    parser.add_argument("--port", type=int, default=5002)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
