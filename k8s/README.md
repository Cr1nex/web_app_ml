# Kubernetes Deployment (hw2)

This setup uses:
- `backend` as a private service (`ClusterIP`) with explicit `NetworkPolicy` ingress rules.
- `frontend` as an internal service behind the NGINX gateway.
- `nginx-gateway` as the public entrypoint (`LoadBalancer`) for both web and API traffic.

## Kind Cluster (3 Nodes)

```bash
kind create cluster --name hw2 --config k8s/kind-config.yaml
```

## Build Images

```bash
docker build -t hw2/backend:latest backend
docker build -t hw2/frontend:latest frontend
```

## Load Images Into Kind

```bash
kind load docker-image --name hw2 hw2/backend:latest hw2/frontend:latest
```

## Apply Manifests

```bash
kubectl apply -k k8s/
kubectl -n hw2 rollout status deployment/backend
kubectl -n hw2 exec deployment/backend -- alembic upgrade head
```

## Access (Local)

```bash
kubectl -n hw2 port-forward svc/nginx-gateway 8080:80
```

- Frontend: `http://127.0.0.1:8080/`
- API docs: `http://127.0.0.1:8080/api/docs`
- Login endpoint: `POST http://127.0.0.1:8080/api/v1/auth/login`

## Networking

- Public routes are exposed only through `nginx-gateway`.
- Backend remains private (`ClusterIP`) and is reachable only from gateway pods due to `NetworkPolicy`.
