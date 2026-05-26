# Docker Compose Configuration

## Architecture

```
  Browser / curl
       │
       ▼  localhost:8080
  ┌─────────────────────────────────────────────────────┐
  │              Docker bridge network: hw2-app-net     │
  │                                                     │
  │  gateway (nginx)  ──/api/*──►  app (FastAPI :8000)  │
  │        │          ──/  * ──►  frontend (nginx :80)  │
  │        │                           app ──► db :5432 │
  │  [only public                      app ──► redis:6379│
  │   container]                       app ──► rabbitmq  │
  └─────────────────────────────────────────────────────┘
```

## Port Map

### External (published to host)
| Host port | Container | Purpose |
|-----------|-----------|---------|
| `8080` | `gateway:80` | Main entry — web app + API |
| `15672` | `rabbitmq:15672` | RabbitMQ management UI |
| `5432` | `db:5432` | Postgres (dev/debug access) |

### Internal only (never published)
| Service | Port | Reached by |
|---------|------|-----------|
| `app` | `8000` | `gateway` only |
| `frontend` | `80` | `gateway` only |
| `redis` | `6379` | `app` |
| `rabbitmq` | `5672` | `app` |

Docker's embedded DNS resolves service names (`redis`, `app`, etc.) to container IPs automatically — no hard-coded addresses needed.

---

## Services

### `db` — PostgreSQL 15
- Stores users, hashed passwords, refresh tokens, game scores.
- Volume `db-data` persists data across restarts.
- Healthcheck (`pg_isready`) gates backend startup — the `app` service will not start until Postgres is fully ready.

### `redis` — Redis 7
- Caches the JWKS public key set and tracks JWT refresh token revocations.
- No host port published — reachable only inside `hw2-app-net` as `redis:6379`.

### `rabbitmq` — RabbitMQ 3
- Receives asynchronous audit-log events from the backend middleware.
- AMQP port `5672` is internal. Management UI port `15672` is published for local inspection.

### `app` — Backend (FastAPI)
- Built from `./backend/Dockerfile`.
- Startup command overrides the Dockerfile `CMD`:
  ```bash
  sh -c "alembic upgrade head && uvicorn api.app:app --host 0.0.0.0 --port 8000"
  ```
  Migrations run automatically every startup before the server starts.
- Depends on `db` (`service_healthy`) and `redis`/`rabbitmq` (`service_started`).
- Port `8000` is **not** published to the host — only the gateway can reach it.

### `frontend` — React (built → Nginx)
- Built from `./frontend/Dockerfile` (multi-stage: Vite compiles, Nginx serves).
- Port `80` is **not** published — accessed only through the gateway.

### `gateway` — Nginx Reverse Proxy
- The **only container with a host port** (`8080:80`).
- Routes traffic based on URL prefix and applies per-endpoint rate limits:

| Route | Backend | Rate limit |
|-------|---------|-----------|
| `POST /api/v1/auth/login` | `app:8000` | 10 req/min |
| `POST /api/v1/auth/register` | `app:8000` | 5 req/min |
| `POST /api/v1/auth/refresh` | `app:8000` | 30 req/min |
| `/api/*` (all others) | `app:8000` | 120 req/min |
| `/*` | `frontend:80` | — |

Config is bind-mounted (`./nginx/default.conf`) read-only — no rebuild needed to change routing rules.

---

## Networks and Volumes

```yaml
networks:
  app-net:
    name: hw2-app-net
    driver: bridge   # all services on one isolated bridge network

volumes:
  db-data:           # named volume — survives container restarts
```

Delete the volume to fully reset the database: `docker compose down -v`
