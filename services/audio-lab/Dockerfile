# syntax=docker/dockerfile:1
# audio-lab on the rack's GTX 1070 (Pascal). A benchmark tool: built on docker-0, never
# pushed or deployed. Build from this directory:
#   docker build --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) -t audio-lab-pascal .
FROM python:3.11-slim-bookworm

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
# uv's download cache lives in a build cache, not the image (torch + CUDA is ~5 GB twice over).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra models-pascal --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra models-pascal

# Fail the build, not the run, if torchvision's compiled ops don't match torch.
RUN python -c "import torch, torchvision; torch.ops.torchvision.nms; print(torch.__version__, torchvision.__version__)"

# Run as the host user (docker run --user) so outputs aren't root-owned; HF_HOME is mounted.
# That uid has no passwd entry here, so USER stops torch's getpass.getuser() from failing.
ENV HF_HOME=/hf HOME=/tmp USER=audio-lab

# There is no .git in the image, so the run records the commit it was built from.
ARG GIT_COMMIT=unknown
ENV AUDIO_LAB_COMMIT=${GIT_COMMIT}

ENTRYPOINT ["audio-lab"]
