FROM python:3.12-slim AS builder

ARG DEBIAN_FRONTEND=noninteractive

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN python -m venv $VIRTUAL_ENV

RUN pip install --no-cache-dir "mlflow>=2.12"


FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV

RUN mkdir -p /app/mlflow /app/artifacts && \
    groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
    chown -R appuser:appgroup /app

USER 10001

EXPOSE 5000

CMD ["mlflow", "server", \
     "--backend-store-uri", "sqlite:////app/mlflow/mlflow.db", \
     "--default-artifact-root", "/app/artifacts", \
     "--serve-artifacts", \
     "--host", "0.0.0.0", \
     "--port", "5000"]
