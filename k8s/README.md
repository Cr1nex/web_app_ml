# Kubernetes Deployment (webml)

This Kustomize tree deploys the full web + ML stack into a 3-node Kind cluster.

> **TL;DR** — from the repo root:
> ```bash
> make kind-up   # create cluster + build all images + load + apply + wait
> make fwd       # port-forward gateway → http://localhost:8080
> ```
> See the [Makefile](../Makefile) for finer-grained targets (`image-mlflow`, `kind-reload`, `kind-down`, …) and how to override `PROJECT` / `CLUSTER` / `TAG`. The sections below show the manual equivalents.


| Pod | Service | Exposed | Notes |
|---|---|---|---|
| `postgres` | ClusterIP `postgres:5432` | — | Two DBs: `appdb` (web), `mlflow` (auto-created on first init by `01-create-mlflow-db.sh`) |
| `redis` | ClusterIP `redis:6379` | — | JWKS + ml-service auth cache |
| `rabbitmq` | ClusterIP `rabbitmq:5672` | — | request telemetry queue |
| `backend` | ClusterIP `backend:8000` | — | FastAPI; proxies `/api/v1/prediction/*` to ml-service |
| `frontend` | ClusterIP `frontend:80` | — | Vite SPA |
| `mlflow` | ClusterIP `mlflow:5000` | — | Tracking server, backend store in `mlflow` DB, artifacts on PVC |
| `ml-service` | ClusterIP `ml-service:5002` | — | Loads model from MLflow registry on cold start |
| `nginx-gateway` | NodePort `30501` → host `8080` | http://localhost:8080 | Single public ingress |

NetworkPolicies pin lateral traffic: backend accepts only from gateway, ml-service only from backend, mlflow only from ml-service. The gateway is the sole public entrypoint.

---

## One-time setup

```bash
# Installs kubectl + kind if missing
bash scripts/setup.sh

# Bring up a 3-node cluster (1 control-plane + 2 workers, port 30501 → 8080)
kind create cluster --name webml --config k8s/kind-config.yaml
```

---

## Build all images

```bash
docker build -t webml/backend:latest    backend
docker build -t webml/frontend:latest   frontend
docker build -t webml/mlflow:latest     -f ml_service/src/deployment/Dockerfile ml_service
docker build -t webml/ml-service:latest ml_service
```

## Load into Kind

```bash
kind load docker-image --name webml \
  webml/backend:latest \
  webml/frontend:latest \
  webml/mlflow:latest \
  webml/ml-service:latest
```

Each load takes 30-60 s — the MLflow + ml-service images are ~1 GB each because of xgboost / lightgbm.

## Apply manifests

```bash
kubectl apply -k k8s/

# Wait for everything to settle (~60 s on a cold cluster)
kubectl -n webml rollout status deployment/postgres
kubectl -n webml rollout status deployment/mlflow
kubectl -n webml rollout status deployment/backend
kubectl -n webml rollout status deployment/ml-service
kubectl -n webml rollout status deployment/frontend
kubectl -n webml rollout status deployment/nginx-gateway
```

The `mlflow` database is auto-created on first Postgres start by the
init script in the `postgres-initdb` ConfigMap. If the postgres PVC
predates this change, the init script won't re-run — create the DB by
hand once:

```bash
kubectl -n webml exec deployment/postgres -- \
  psql -U appuser -d appdb -c "CREATE DATABASE mlflow OWNER appuser;"
kubectl -n webml rollout restart deployment/mlflow
```

## Access

```bash
# Web app + API
kubectl -n webml port-forward svc/nginx-gateway 8080:80
#   Frontend:  http://127.0.0.1:8080/
#   API docs:  http://127.0.0.1:8080/api/docs
#   Login:     POST http://127.0.0.1:8080/api/v1/auth/login

# MLflow UI (private — port-forward to view)
kubectl -n webml port-forward svc/mlflow 5000:5000
#   http://127.0.0.1:5000

# ml-service (private — only for debugging)
kubectl -n webml port-forward svc/ml-service 5002:5002
#   http://127.0.0.1:5002/docs
```

---

## Train and push a model into the cluster

Same workflow as the docker-compose flow — only the tracking URI changes.
The MLflow container's artifact proxy means the trainer never needs PVC
access; everything is HTTP.

```bash
# Terminal 1 — keep this open
kubectl -n webml port-forward svc/mlflow 5000:5000
```

```bash
# Terminal 2 — runs against your local Python
cd ml_service
export MLFLOW_TRACKING_URI=http://localhost:5000

# Build features (needs the raw CSV under data/raw/)
python -m src.data.transaction_features

# Train with CV — logs run + registers @staging
python -m src.services.train --cv

# Inspect, then promote the version you want to @champion
python -m src.services.registry list
python -m src.services.registry promote --version N

# Tell the ml-service pods to hot-swap
kubectl -n webml exec deployment/ml-service -- \
  curl -sX POST http://localhost:5002/api/v1/reload
```

The reload is per-pod, so for multi-replica ml-service either roll the
deployment (`kubectl -n webml rollout restart deployment/ml-service`) or
hit `/reload` on each pod via `kubectl exec`. The first request after
reload may take ~2 s while the pyfunc loads the new model from MLflow.

---

## Teardown

```bash
kind delete cluster --name webml
```

This wipes all PVCs (Postgres `appdb` + `mlflow`, MLflow artifacts) and
images loaded into Kind. The cached image layers in your host Docker
daemon survive.
