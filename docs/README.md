# HW2 — Auth Microservice

A personal portfolio site backed by a production-grade(!) auth microservice: React + FastAPI + PostgreSQL + Redis + RabbitMQ + NGINX, deployed on Kubernetes (Kind) or Docker Compose.



## Quick Summary!!!

This is a web application with authentication that has alembic, rabbitmq logging, key rotation jwks, public key caching inside redis,docker user perms isolation, postgre for user credentials.
Kind for cluster management (with the kubernetes version), docker-compose.yml for the normal version, nginx reverse proxy serving static files. Docker internal bridge network, login page, a page that has a snake game, i liked the hw, so i did a little more then expected.

The envs are in docker as its just a in dev web application not intended for prod

you can just docker-compose up -d --build for easy test

## Important!!!
- Dockerfiles are under src/

- 2 versions with and without kubernetes

- I also used ai a bit but because i already had the project structure in mind its just a tool as i have done similar projects like this without ai



![alt text](<Screenshot 2026-05-18 130035.png>)
![alt text](image.png)
![alt text](<Screenshot 2026-05-18 125518.png>)
![alt text](<Screenshot 2026-05-18 125547.png>)
![alt text](<Screenshot 2026-05-18 125704.png>)
## Run it (Docker Compose)

```bash
docker compose up --build
```

Migrations run automatically on startup — no extra step needed.

| URL | What |
|-----|------|
| http://localhost:8080 | App (portfolio + auth) |
| http://localhost:8080/api/docs | Swagger UI |
| http://localhost:15672 | RabbitMQ UI (guest / guest) |

Stop and wipe data:

```bash
docker compose down -v
```

---

## Run it (Kubernetes / Kind)

> Stop Compose first: `docker compose down`

**1. Create the cluster**
```powershell
kind create cluster --config k8s/kind-config.yaml --name hw2
```

**2. Build images**
```powershell
$env:DOCKER_BUILDKIT = "0"
docker build -t hw2/backend:latest ./backend
docker build -t hw2/frontend:latest ./frontend
```

**3. Load images into the cluster**
```powershell
docker save hw2/backend:latest -o backend.tar
docker save hw2/frontend:latest -o frontend.tar
foreach ($node in "hw2-control-plane","hw2-worker","hw2-worker2") {
    docker cp backend.tar "${node}:/backend.tar"
    docker exec $node ctr --namespace k8s.io images import /backend.tar
    docker cp frontend.tar "${node}:/frontend.tar"
    docker exec $node ctr --namespace k8s.io images import /frontend.tar
}
Remove-Item backend.tar, frontend.tar
```

**4. Deploy**
```powershell
kubectl apply -k k8s/
```

Migrations run automatically before the backend starts. App is at **http://localhost:8080**

After code changes, repeat steps 2–3 then:
```powershell
kubectl rollout restart deployment/backend deployment/frontend -n hw2
```

Tear down:
```powershell
kind delete cluster --name hw2
```

---

## Inspect the databases

Run each in a separate terminal, then connect with any local client:

```powershell
# Postgres — connect with psql or any DB client at localhost:5432
kubectl port-forward -n hw2 svc/postgres 5432:5432

# Redis — connect with redis-cli or RedisInsight at localhost:6379
kubectl port-forward -n hw2 svc/redis 6379:6379

# RabbitMQ management UI — open http://localhost:15672 (guest / guest)
kubectl port-forward -n hw2 svc/rabbitmq 15672:15672
```

---

## API

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | — | Health check |
| POST | `/api/v1/auth/register` | — | Create account |
| POST | `/api/v1/auth/login` | — | Login, returns JWT pair |
| POST | `/api/v1/auth/refresh` | Refresh token | Rotate refresh token |
| GET | `/api/v1/auth/jwks` | — | Public JWKS keys |

### Game

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/game/scores` | Bearer JWT | Save a Snake game score |
| GET | `/api/v1/game/scores/leaderboard` | — | Top scores (public) |

Quick test:
```bash
curl -s -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"ChangeMe123!"}'
```
