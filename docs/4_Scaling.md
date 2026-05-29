# Scaling and Load Balancing

## Why the App Scales Horizontally

The FastAPI backend is **stateless** — no session data lives in the process. All shared state is external:

| State | Store |
|-------|-------|
| Users, scores | PostgreSQL |
| JWT tokens, JWKS cache | Redis |
| Audit events | RabbitMQ |

Any number of backend replicas can handle any request without coordination.

---

## Load Balancing via Nginx

The Nginx gateway sits in front of all traffic. It distributes requests across backend instances using **round-robin**:

- **Docker Compose:** Docker's embedded DNS returns a rotating list of IPs for the hostname `app` when multiple containers exist. Nginx picks the next one per request.
- **Kubernetes:** The `backend` Service's ClusterIP is backed by kube-proxy iptables rules that DNAT connections to healthy pod IPs in round-robin order.

No Nginx config changes are required in either case — scaling is transparent to the gateway.

### Rate Limiting (always active regardless of scale)

| Endpoint | Limit | Burst |
|----------|-------|-------|
| `POST /api/v1/auth/login` | 10 req/min/IP | 5 |
| `POST /api/v1/auth/register` | 5 req/min/IP | 2 |
| `POST /api/v1/auth/refresh` | 30 req/min/IP | 10 |
| `/api/*` (all others) | 120 req/min/IP | 20 |

Returns `HTTP 429` when exceeded.

---

## Scaling with Docker Compose

```bash
# Scale backend to 3 instances
docker compose up -d --scale app=3

# Scale both backend and frontend
docker compose up -d --scale app=3 --scale frontend=2

# Return to 1 instance
docker compose up -d --scale app=1
```

The `app` service has no fixed host port, so multiple containers start without conflict. Docker DNS (`server app:8000` in nginx.conf) automatically covers all instances.

---

## Scaling with Kubernetes

```bash
# Scale backend to 5 replicas
kubectl scale deployment backend --replicas=5 -n webml

# Scale frontend
kubectl scale deployment frontend --replicas=3 -n webml
```

Kubernetes only routes traffic to **Ready** pods (readiness probe `GET /health` must pass). New replicas run the init container (migrations) then enter the load-balanced Endpoints list automatically.

### Auto-Scaling (HPA)

```bash
# Autoscale between 2–10 replicas at 60% CPU target
kubectl autoscale deployment backend --min=2 --max=10 --cpu-percent=60 -n webml

# Check status
kubectl get hpa -n webml
```

Requires the Metrics Server in the cluster.

### Zero-Downtime Rollouts

```bash
kubectl rollout restart deployment/backend -n webml   # rolling update
kubectl rollout undo    deployment/backend -n webml   # rollback if broken
```

New pods come up and pass readiness probes before old pods are terminated — no gap in availability.

---

## Summary

| | Docker Compose | Kubernetes |
|--|---------------|-----------|
| Scale command | `--scale app=N` | `kubectl scale --replicas=N` |
| Load balancing | Docker DNS round-robin | kube-proxy iptables NAT |
| Auto-scale | Manual | HPA (CPU/memory) |
| Health-gated traffic | No | Yes (readiness probes) |
| Rolling updates | Manual (stop/start) | `kubectl rollout restart` |
