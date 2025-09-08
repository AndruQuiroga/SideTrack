# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build dependencies and shared system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
# Copy project metadata and sources
COPY pyproject.toml ./
COPY sidetrack ./sidetrack

# Build wheels for the core package and dependencies
RUN pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Provide the cached wheels for downstream images
COPY --from=builder /wheels /wheels

WORKDIR /app
