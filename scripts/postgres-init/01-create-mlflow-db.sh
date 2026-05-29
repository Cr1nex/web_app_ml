#!/bin/sh
# Idempotent: only creates the mlflow database if it doesn't already exist.
# Files in /docker-entrypoint-initdb.d/ run once when the postgres data
# directory is first initialised; this guard makes manual re-runs safe too.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
SELECT 'CREATE DATABASE mlflow OWNER appuser'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')
\gexec
EOSQL
