#!/usr/bin/env bash
set -euo pipefail

echo "[api] Applying migrations..."
alembic upgrade head

echo "[api] Starting API server..."
exec uvicorn apps.api.main:create_app --factory --host 0.0.0.0 --port 8000
