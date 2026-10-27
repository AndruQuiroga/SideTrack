# syntax=docker/dockerfile:1
# Sidetrack's gpu-queue worker: the sidetrack sources plus PyTorch for the rack's GTX 1070.
# Build from the repository root:
#   docker build -f services/gpu-worker/Dockerfile -t sidetrack-gpu .
#   docker build -f services/gpu-worker/Dockerfile --target test -t sidetrack-gpu-test .
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:/root/.local/bin:$PATH"

# ffmpeg decodes webm and m4a; libsndfile handles the rest.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app
# Dependencies only; uv's download cache stays in a build cache, not the image.
COPY pyproject.toml README.md ./
COPY services/gpu-worker/pyproject.toml services/gpu-worker/uv.lock services/gpu-worker/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --project services/gpu-worker --no-install-package sidetrack

# Fail the build, not a job, if torchvision's compiled ops don't match torch.
RUN python -c "import torch, torchvision; torch.ops.torchvision.nms; print(torch.__version__, torchvision.__version__)"

# Run from the sources, like the API image (the root package itself isn't installed).
COPY sidetrack ./sidetrack
RUN python -c "import sidetrack.worker, sidetrack.analysis.embeddings.muq_mulan"

# Runs as a host uid without a passwd entry: USER keeps torch's getpass.getuser() working.
# HF_HOME is a mounted volume holding the pinned weights.
ENV HF_HOME=/hf HOME=/tmp USER=sidetrack
CMD ["python", "-m", "sidetrack.worker", "--queues", "gpu"]

# The GPU parity test against an audio-lab run (services/gpu-worker/tests).
FROM base AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --project services/gpu-worker --no-install-package sidetrack
COPY services/gpu-worker/tests services/gpu-worker/tests
WORKDIR /app/services/gpu-worker
ENV PYTHONPATH=/app
ENTRYPOINT ["pytest", "-m", "gpu"]
CMD []

# The default target, last so a plain `docker build` (and CI) produces the worker image.
FROM base AS runtime
