# Deployment and Usage

The app is exposed at `http://localhost:8080` in both deployment modes.

---

## Option A — Docker Compose

### Prerequisites
Docker Desktop 24+ with Compose v2.

### Start

```bash
# From the project root — builds images and starts all containers
docker compose up -d --build

# Watch startup logs
docker compose logs -f

# Confirm all containers are up
docker compose ps
```

Startup order: `db` (waits for healthcheck) → `app` (runs migrations, then starts Uvicorn) → `frontend` + `gateway`.

### Access

| URL | What |
|-----|------|
| `http://localhost:8080` | Web app (landing, auth, Snake game) |
| `http://localhost:8080/api/docs` | Swagger UI |
| `http://localhost:8080/health` | `{"status":"ok"}` |
| `http://localhost:15672` | RabbitMQ UI (`guest` / `guest`) |

### Test with curl

```bash
# Health check
curl -s http://localhost:8080/health

# Register
curl -s -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"ChangeMe123!"}'

# Login (returns access_token + refresh_token in response body)
curl -s -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"ChangeMe123!"}'

# Refresh — rotate the refresh token (replace <token> with value from login response)
curl -s -X POST http://localhost:8080/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<token>"}'

# JWKS — public signing keys used to verify JWTs
curl -s http://localhost:8080/api/v1/auth/jwks

# Leaderboard (public)
curl -s http://localhost:8080/api/v1/game/scores/leaderboard
```

### Stop

```bash
docker compose down        # stops containers, keeps data
docker compose down -v     # stops containers AND deletes the database volume
```

---

## Option B — Kubernetes (Kind)

### Prerequisites
Docker Desktop + `kubectl` + `kind`.

### Port Flow (Kubernetes)

```
localhost:8080
     │
     │  kind maps hostPort 8080 → NodePort 30501 on control-plane node
     ▼
nginx-gateway (NodePort :30501 → pod :80)
     │
     ├── /api/*  → backend Service (ClusterIP :8000) → backend pods
     └── /*      → frontend Service (ClusterIP :80)  → frontend pods

All other services (postgres, redis, rabbitmq) are ClusterIP — no external access.
NetworkPolicy: backend pods only accept traffic from nginx-gateway pods.
```

### Step 1 — Create Cluster

```bash
kind create cluster --name webml --config k8s/kind-config.yaml
```

### Step 2 — Build Images

```bash
# PowerShell
$env:DOCKER_BUILDKIT = "0"
docker build -t webml/backend:latest  ./backend
docker build -t webml/frontend:latest ./frontend
```

### Step 3 — Load Images into Kind

```bash
kind load docker-image --name webml webml/backend:latest
kind load docker-image --name webml webml/frontend:latest
```

If `kind load` fails on Windows, use the manual tar method:

```powershell
docker save webml/backend:latest  -o backend.tar
docker save webml/frontend:latest -o frontend.tar
foreach ($node in "webml-control-plane","webml-worker","webml-worker2") {
    docker cp backend.tar  "${node}:/backend.tar"
    docker exec $node ctr --namespace k8s.io images import /backend.tar
    docker cp frontend.tar "${node}:/frontend.tar"
    docker exec $node ctr --namespace k8s.io images import /frontend.tar
}
Remove-Item backend.tar, frontend.tar
```

### Step 4 — Deploy

```bash
kubectl apply -k k8s/

# Wait for backend (init container runs migrations automatically)
kubectl -n webml rollout status deployment/backend
```

### Step 5 — Verify

```bash
kubectl get pods -n webml
curl -s http://localhost:8080/health
```

### Useful Debug Commands

```bash
# Logs
kubectl logs -n webml -l app=backend --follow
kubectl logs -n webml -l app=backend -c migrate   # init container (migrations)

# Shell into backend pod
kubectl exec -it -n webml deployment/backend -- bash

# Temporary port-forward to inspect databases
kubectl port-forward -n webml svc/postgres  5432:5432
kubectl port-forward -n webml svc/redis     6379:6379
kubectl port-forward -n webml svc/rabbitmq  15672:15672
```

### After Code Changes

```bash
docker build -t webml/backend:latest  ./backend
docker build -t webml/frontend:latest ./frontend
kind load docker-image --name webml webml/backend:latest webml/frontend:latest
kubectl rollout restart deployment/backend deployment/frontend -n webml
```

### Tear Down

```bash
kind delete cluster --name webml
```

---

## Compose vs Kubernetes — Quick Comparison

| | Docker Compose | Kubernetes (Kind) |
|--|---------------|-------------------|
| Entry point | `localhost:8080` | `localhost:8080` |
| Migrations | Command override in `app` service | Init container in backend pod |
| Network isolation | Bridge network, no NetworkPolicy | ClusterIP + NetworkPolicy (backend deny-all) |
| Health checking | `healthcheck:` on `db` only | Readiness + liveness probes on all pods |
| Data persistence | Named volume `db-data` | PersistentVolumeClaim 10 Gi |
