# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for building and running the API
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends build-essential libpq-dev \ 
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata and source for installation
COPY pyproject.toml README.md ./
COPY sidetrack ./sidetrack
COPY apps ./apps

# Install Python dependencies with the API extras
RUN pip install --upgrade pip \
    && pip install --no-cache-dir ".[api]"

# Copy application code and migrations
COPY alembic.ini ./
COPY migrations ./migrations

# Ensure Alembic looks in the in-image migrations directory
RUN sed -i 's#^script_location\s*=.*#script_location = migrations#' alembic.ini

EXPOSE 8000

CMD [\
  "uvicorn",\
  "apps.api.main:create_app",\
  "--factory",\
  "--host",\
  "0.0.0.0",\
  "--port",\
  "8000"\
]
