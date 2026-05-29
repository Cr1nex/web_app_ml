"""
Smoke tests for the FastAPI prediction routes.

We don't spin up MLflow — instead we inject the test-fixture booster
directly into `src.api.v1.app.model` and exercise the routes via
FastAPI's TestClient. This keeps the suite fast and hermetic.
"""

import os

import pytest
from fastapi.testclient import TestClient

from src.data.transaction_features import CATEGORICAL_FEATURES
from src.services.inference import CategoricalTreeModel


@pytest.fixture
def client(trained_xgb):
    """Importing the app triggers FastAPI startup; we patch the model in afterwards."""
    os.environ["ML_AUTH_ENABLE_AUTH"] = "false"

    import src.api.v1.app as app_module
    app_module.model = CategoricalTreeModel(trained_xgb, CATEGORICAL_FEATURES)

    with TestClient(app_module.app) as c:
        yield c

    app_module.model = None


def test_health_reports_model_loaded(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "model_loaded": True}


def test_single_prediction(client):
    body = {
        "features": {
            "town": "Avon",
            "property_type": "Residential",
            "residential_type": "Single Family",
            "assessed_value": 200000,
            "list_year": 2021,
            "month_recorded": 6,
        }
    }
    r = client.post("/api/v1/predict", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 1
    assert len(data["predictions"]) == 1
    assert data["predictions"][0] > 0


def test_batch_prediction(client):
    body = {
        "instances": [
            {
                "town": "Avon",
                "property_type": "Residential",
                "residential_type": "Single Family",
                "assessed_value": 200000,
                "list_year": 2021,
                "month_recorded": 6,
            },
            {
                "town": "Stamford",
                "property_type": "Residential",
                "residential_type": "Condo",
                "assessed_value": 350000,
                "list_year": 2023,
                "month_recorded": 9,
            },
        ]
    }
    r = client.post("/api/v1/predict/batch", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 2
    assert len(data["predictions"]) == 2


def test_predict_rejects_invalid_payload(client):
    """Missing required field returns 422, not 500."""
    r = client.post("/api/v1/predict", json={"features": {"town": "Avon"}})
    assert r.status_code == 422


def test_predict_503_when_model_unloaded(client):
    """If the model handle is None, the API surfaces a clean 503."""
    import src.api.v1.app as app_module
    saved = app_module.model
    app_module.model = None
    try:
        r = client.post("/api/v1/predict", json={
            "features": {
                "town": "Avon",
                "property_type": "Residential",
                "residential_type": "Single Family",
                "assessed_value": 200000,
                "list_year": 2021,
                "month_recorded": 6,
            }
        })
        assert r.status_code == 503
    finally:
        app_module.model = saved
