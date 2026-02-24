# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04 AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       python3.11 python3.11-dev python3.11-venv \
       build-essential libsndfile1 curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

FROM base AS deps

COPY services/extraction/pyproject.toml services/extraction/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM base AS runtime
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=deps /opt/venv /opt/venv
COPY services/extraction/src ./src

EXPOSE 8800

CMD ["uvicorn", "extraction.app:app", "--host", "0.0.0.0", "--port", "8800"]
