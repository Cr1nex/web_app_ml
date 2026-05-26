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
python -m src.data.features
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

```bash
# Build and start all services
docker-compose up --build -d

# Check status
docker-compose ps

# View MLflow UI
# Open http://localhost:5000

# View API docs
# Open http://localhost:5002/docs

# Stop everything
docker-compose down
```

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
│   │   └── features.py                # Feature engineering pipeline
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
      "year": 2020, "month": 6, "quarter": 2,
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
      "median_sales_ratio": 0.92
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

1. **Chronological splitting** — Train on 2001–2017, validate on 2018–2019, test on 2020+. No random shuffling to prevent temporal data leakage.
2. **Per-town features** — Lag and rolling features computed per town to avoid cross-location leakage.
3. **Pydantic configs** — All configuration is type-validated via Pydantic models under `src/configs/`.
4. **MLflow aliases** — Uses `@champion` / `@staging` aliases (MLflow 2.x) instead of deprecated stage transitions.
5. **KS-test drift detection** — Kolmogorov-Smirnov test on feature distributions to detect market shifts.
