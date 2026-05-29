# Property Valuation MLflow Lifecycle Project

End-to-end MLOps pipeline for real estate price forecasting with full MLflow lifecycle management: **tracking → registry → serving → monitoring**, automated via Airflow and deployed with Docker.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- (Optional) Kaggle CLI for dataset download

### 1. Clone & Setup Virtual Environment

```bash
cd c:\Users\blank\projects\mlops\term

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 2. Get the Dataset

Download the **Real Estate Sales 2001-2023** dataset from the Connecticut Open Data portal (no account needed):
- **Direct CSV download**: https://data.ct.gov/api/views/5mzw-sjtu/rows.csv?accessType=DOWNLOAD
- **Dataset page**: https://catalog.data.gov/dataset/real-estate-sales-2001-2023-gl

Place the CSV file in `data/raw/` and rename it:
```bash
# Download directly via curl
curl -L -o data/raw/Real_Estate_Sales_2001-2021_GL.csv "https://data.ct.gov/api/views/5mzw-sjtu/rows.csv?accessType=DOWNLOAD"
```

### 3. Run Locally (Without Docker)

**Step 1 — Start MLflow tracking server:**
```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./artifacts --host 0.0.0.0 --port 5000
```

**Step 2 — Build feature matrix** (open a new terminal):
```bash
python -m src.data.transaction_features
```

**Step 3 — Train baseline model:**
```bash
python -m src.services.train
# With time-series cross-validation:
python -m src.services.train --cv
# With LightGBM:
python -m src.services.train --model-type lightgbm
```

**Step 4 — View results in MLflow UI:**
Open http://localhost:5000 in your browser.

**Step 5 — Hyperparameter tuning:**
```bash
python -m src.services.tune --max-evals 20
python -m src.services.tune --max-evals 10 --model-type lightgbm
```

**Step 6 — Start the prediction API:**
```bash
uvicorn src.api.v1.app:app --port 5002 --reload
```
- Swagger docs: http://localhost:5002/docs
- Health check: http://localhost:5002/api/v1/health

**Step 7 — Run production monitoring:**
```bash
# With API running:
python -m src.deployment.monitor --n-batches 10

# Without API (direct model loading):
python -m src.deployment.monitor --no-api --n-batches 10
```

---

### 4. Run with Docker

There are two compose files:

| File | Use it when | MLflow backend store |
|---|---|---|
| `docker-compose.yml` (repo root) | Running the **full app + MLflow stack** together | Postgres (the existing `db` service) |
| `ml_service/docker-compose.yml` | Running **only** the ML service in isolation | SQLite (inside the container) |

Full-stack (recommended):
```bash
# From repo root
docker compose up --build -d
docker compose ps
# MLflow UI:   http://localhost:5000
# API docs:    http://localhost:5002/docs
# Web app:     http://localhost:8080
```

The first time the `db` volume is created, the init script in
`scripts/postgres-init/` automatically creates a separate `mlflow` database
inside the existing Postgres container, so MLflow metadata stays out of the
application schema.

If you already have a populated `db-data` volume from before this change,
the init script won't re-run. Create the database once by hand:
```bash
docker compose exec db psql -U appuser -d appdb -c "CREATE DATABASE mlflow OWNER appuser;"
docker compose restart mlflow
```

Stand-alone ML-only stack (no app, sqlite store):
```bash
cd ml_service
docker compose up --build -d
```

---

### 5. Train and push a model into the running Docker stack

`docker compose up -d` starts two containers: `mlflow-server` (the tracking
server + registry, port 5000) and `valuation-api` (the prediction API, port
5002, which loads its model over HTTP from `mlflow-server`). The MLflow data
lives in named volumes (`mlflow_data`, `mlflow_artifacts`), so models survive
container restarts and don't need to be baked into the image.

**Workflow** — train locally, register through the container's MLflow API,
then tell the prediction container to hot-reload:

```bash
# 1. Bring up the stack (one-time)
cd ml_service
docker compose up -d

# 2. Point your local Python at the containerised MLflow server
export MLFLOW_TRACKING_URI=http://localhost:5000

# 3. Build the feature parquet (cached under data/processed/)
python -m src.data.transaction_features

# 4. Train + auto-register as @staging
python -m src.services.train --cv
#   ↳ logs run to MLflow, registers a new version of PropertyValuationModel,
#     sets alias @staging on it.

# 5. (Optional) tune and let the best run register itself
python -m src.services.tune --max-evals 20

# 6. List versions, decide which one to promote
python -m src.services.registry list

# 7. Promote a version to @champion
python -m src.services.registry promote --version N

# 8. Hot-swap the model inside the running API container — no restart
curl -X POST http://localhost:5002/api/v1/reload
#   ↳ valuation-api re-runs load_production_model() against
#     @champion → @staging → latest and atomically swaps the global handle.
```

**Why this works without rebuilding the image**

- `mlflow-server` accepts any client (local Python, another container, the
  Airflow worker) that hits `http://mlflow:5000` from inside the network or
  `http://localhost:5000` from the host. Registering a model writes to the
  `mlflow_data` volume; artifacts go to `mlflow_artifacts`.
- `valuation-api` loads the model via `mlflow.pyfunc.load_model("models:/…@champion")`.
  That call streams the artifact over HTTP from `mlflow-server`, so the API
  container never needs the artifact on disk.
- `POST /api/v1/reload` is the only step that actually swaps the model. If
  the alias hasn't been moved, reload is a no-op.

**Troubleshooting**

| Symptom | Likely cause | Fix |
|---|---|---|
| `RuntimeError: Cannot reach MLflow` at API startup | `mlflow-server` not healthy yet | `docker compose logs mlflow` and wait for the health check |
| `No registered versions found for 'PropertyValuationModel'` | Trained against a different tracking URI | Re-run training with `MLFLOW_TRACKING_URI=http://localhost:5000` |
| Reload returns 503 | Alias not set or run artifact missing | `python -m src.services.registry list` and re-promote |

---

## Project Structure

```
term/
├── data/
│   ├── raw/                           # Raw dataset CSV (git-ignored)
│   └── processed/                     # Feature-engineered parquet
├── dags/
│   └── property_valuation_dag.py      # Airflow DAGs (training + monitoring)
├── src/
│   ├── __init__.py
│   ├── config.py                      # Backward-compatible re-exports
│   ├── configs/                       # Pydantic configuration models
│   │   ├── paths.py                   # Directory paths
│   │   ├── dataset.py                 # Column mappings, split dates
│   │   ├── features.py                # Lag/rolling window params
│   │   ├── mlflow_config.py           # Tracking URI, experiment names
│   │   ├── training.py                # CV splits, random state
│   │   ├── monitoring.py              # Drift thresholds
│   │   └── models/
│   │       ├── xgboost_config.py      # XGBoost hyperparameters
│   │       ├── lightgbm_config.py     # LightGBM hyperparameters
│   │       └── api_models.py          # API request/response schemas
│   ├── api/
│   │   └── v1/
│   │       ├── app.py                 # FastAPI application
│   │       └── routes.py              # API route handlers
│   ├── data/
│   │   └── transaction_features.py    # Per-transaction feature pipeline
│   ├── services/
│   │   ├── model.py                   # Model factories & evaluation
│   │   ├── train.py                   # Training with MLflow tracking
│   │   └── tune.py                    # Hyperopt tuning + nested runs
│   ├── deployment/
│   │   ├── Dockerfile                 # MLflow server container
│   │   └── monitor.py                 # Production drift monitoring
│   └── notebooks/                     # EDA notebooks
├── Dockerfile                         # API container
├── docker-compose.yml                 # Multi-service deployment
├── requirements.txt
├── README.md
└── .gitignore
```

---

## MLflow Lifecycle Stages

| Stage | Action | Command |
|-------|--------|---------|
| **Track** | Log params, metrics, artifacts | `python -m src.services.train` |
| **Tune** | Hyperparameter search (nested runs) | `python -m src.services.tune --max-evals 20` |
| **Register** | Best model → Registry (auto by tune.py) | Automatic after tuning |
| **Stage** | Promote to Staging alias | Automatic after tuning |
| **Deploy** | Serve as REST API | `uvicorn src.api.v1.app:app --port 5002` |
| **Monitor** | Track drift & degradation | `python -m src.deployment.monitor` |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/predict` | Single property prediction |
| POST | `/api/v1/predict/batch` | Batch predictions |
| GET | `/api/v1/model-info` | Loaded model metadata |

**Example prediction request:**
```bash
curl -X POST http://localhost:5002/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "town": "Avon",
      "property_type": "Residential",
      "residential_type": "Single Family",
      "assessed_value": 217640,
      "list_year": 2020,
      "month_recorded": 9
    }
  }'
```

---

## Airflow Automation

Two DAGs are defined in `dags/property_valuation_dag.py`:

| DAG | Schedule | Tasks |
|-----|----------|-------|
| `property_valuation_training_pipeline` | Weekly (Mon 6AM) | features → train → tune |
| `property_valuation_monitoring` | Daily (8AM) | health_check → monitoring |

To use with Airflow:
```bash
# Set Airflow home and init
export AIRFLOW_HOME=$(pwd)/airflow_home
airflow db init
airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com

# Copy/symlink the DAG
cp dags/property_valuation_dag.py $AIRFLOW_HOME/dags/

# Start scheduler and webserver
airflow scheduler &
airflow webserver --port 8080
```

Airflow UI: http://localhost:8080

---

## Key Design Decisions

1. **Per-transaction regression** — Each training row is one real-estate transaction; the target is the realised sale price. The model takes the six fields a frontend user actually knows (town, property type, residential type, assessed value, list year, month) and returns a dollar estimate.
2. **Chronological splitting** — Splits are by `Date Recorded`, not random, so train/val/test never overlap in time.
3. **Native categorical handling** — `town`, `property_type` and `residential_type` are passed as pandas `category` dtype straight into XGBoost (`enable_categorical=True`, `tree_method="hist"`) or LightGBM (`categorical_feature=…`) — no one-hot blow-up.
4. **Pydantic configs** — All configuration is type-validated via Pydantic models under `src/configs/`.
5. **MLflow aliases** — Uses `@champion` / `@staging` aliases (MLflow 2.x) instead of deprecated stage transitions.
6. **KS-test drift detection** — Kolmogorov-Smirnov test on feature distributions to detect market shifts.
