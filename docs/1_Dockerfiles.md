# Dockerfiles

## Backend (`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY alembic ./alembic
COPY alembic.ini .

ENV PYTHONPATH=/app/src

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
    chown -R appuser:appgroup /app

USER 10001

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Instruction | Purpose |
|---|---|
| `python:3.11-slim` | Lightweight base (~130 MB vs ~900 MB for the full image) |
| `PYTHONDONTWRITEBYTECODE=1` | Skip `.pyc` cache files inside the container |
| `PYTHONUNBUFFERED=1` | Flush logs immediately to `docker logs` / `kubectl logs` |
| `COPY requirements.txt` first | Layer-cache trick: `pip install` is skipped if deps didn't change |
| `--no-cache-dir` | Keeps the image layer smaller by not writing pip's HTTP cache |
| `PYTHONPATH=/app/src` | Lets Python resolve `import api.app`, `import core…` without installing the package |
| Non-root user UID 10001 | Principle of least privilege; numeric UID works with Kubernetes `runAsUser` |
| `EXPOSE 8000` | Documents the port — does not publish it; Compose/K8s handle that |
| `--host 0.0.0.0` | Binds to all interfaces so traffic can reach Uvicorn from outside the container |

> In Docker Compose the `CMD` is overridden to run migrations first:
> `sh -c "alembic upgrade head && uvicorn api.app:app --host 0.0.0.0 --port 8000"`
> In Kubernetes an **init container** runs `alembic upgrade head` before the main pod starts.

---

## Frontend (`frontend/Dockerfile`) — Multi-Stage Build

```dockerfile
# Stage 1 — compile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build          # produces /app/dist

# Stage 2 — serve
FROM nginx:1.27-alpine
RUN addgroup -g 10001 appgroup && adduser -u 10001 -G appgroup -S -D appuser
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Why two stages?**

```
Stage 1 (node:20-alpine)          Stage 2 — final image (nginx:alpine)
  node_modules/ ~280 MB     ──►   /usr/share/nginx/html/  (~25 MB total)
  src/ TypeScript source          index.html, assets/*.js, assets/*.css
  dist/ compiled output    only dist/ crosses the boundary
```

The final image ships with **no Node.js, no source code, no node_modules** — only compiled static assets and Nginx.

| Instruction | Purpose |
|---|---|
| `COPY package.json` first | Same layer-cache trick: `npm install` is skipped if deps didn't change |
| `npm run build` | Vite compiles TypeScript, bundles React, tree-shakes, content-hashes filenames |
| `COPY --from=build` | Only this crosses from Stage 1; everything else is discarded |
| `nginx.conf` (`try_files $uri /index.html`) | SPA fallback — all paths serve `index.html` so React Router handles routing client-side |
| `daemon off` | Required: if Nginx daemonizes, the container exits immediately |

---

## Port Summary

| Image | Container port | Role |
|-------|---------------|------|
| `webml/backend` | `8000` | Uvicorn / FastAPI |
| `webml/frontend` | `80` | Nginx static server |

## Build Commands

```bash
docker build -t webml/backend:latest  ./backend
docker build -t webml/frontend:latest ./frontend
```
