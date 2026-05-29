FROM python:3.12-slim AS builder

ARG DEBIAN_FRONTEND=noninteractive

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN python -m venv $VIRTUAL_ENV

# psycopg2-binary lets MLflow use a postgres backend store; falls back
# transparently to sqlite when the URI is sqlite://.
RUN pip install --no-cache-dir "mlflow>=2.12" "psycopg2-binary>=2.9"


FROM python:3.12-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Defaults — overridden by the compose file when postgres is available.
ENV MLFLOW_BACKEND_STORE_URI=sqlite:////app/mlflow/mlflow.db \
    MLFLOW_ARTIFACTS_DESTINATION=/app/artifacts

WORKDIR /app

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV

RUN mkdir -p /app/mlflow /app/artifacts && \
    groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
    chown -R appuser:appgroup /app

USER 10001

EXPOSE 5000

# JSON form for signal safety; `sh -c … exec …` lets the env vars expand
# while SIGTERM still reaches the mlflow process directly.
CMD ["sh", "-c", "exec mlflow server --backend-store-uri \"$MLFLOW_BACKEND_STORE_URI\" --default-artifact-root mlflow-artifacts:/ --artifacts-destination \"$MLFLOW_ARTIFACTS_DESTINATION\" --serve-artifacts --host 0.0.0.0 --port 5000"]
