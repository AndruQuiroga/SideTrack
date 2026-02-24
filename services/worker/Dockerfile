# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy

WORKDIR /app

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base AS deps

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --extra worker --no-install-project

FROM base AS runtime
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=deps /opt/venv /opt/venv
COPY services/__init__.py ./services/__init__.py
COPY services/api ./services/api
COPY services/worker ./services/worker

EXPOSE 8700

CMD ["python", "-m", "services.worker"]
