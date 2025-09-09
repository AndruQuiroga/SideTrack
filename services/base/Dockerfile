# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies and shared system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Ensure modern packaging tooling
RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /src
# Copy project metadata and sources
COPY pyproject.toml ./
COPY sidetrack ./sidetrack

# Build wheels for the core package and all extras so downstream builds don't
# need internet access to resolve dependencies
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
    '.[api]' '.[worker]' '.[scheduler]' '.[extractor]' \
    && ls -l /wheels

# Verify critical dependency wheels exist to support offline installs later
RUN python - <<'PY'
import glob, sys
required = [
    'sidetrack',
    'uvicorn',
    'fastapi',
    'rq',
    'redis',
    'typer',
    'schedule',
]
missing = [name for name in required if not glob.glob(f'/wheels/{name}-*.whl')]
if missing:
    print('Missing wheels:', missing)
    sys.exit(1)
print('Wheels OK')
PY

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Provide the cached wheels for downstream images
COPY --from=builder /wheels /wheels

WORKDIR /app
