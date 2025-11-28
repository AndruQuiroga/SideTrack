# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy

WORKDIR /app

# System dependencies for building and running the API
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for dependency management
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base AS deps

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev --extra api --no-install-project

FROM base AS runtime
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=deps /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY apps/api ./apps/api
COPY apps/api/entrypoint.sh ./entrypoint.sh

# Ensure Alembic looks in the in-image migrations directory
RUN sed -i 's#^script_location\s*=.*#script_location = migrations#' alembic.ini
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
