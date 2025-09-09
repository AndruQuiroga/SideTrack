# syntax=docker/dockerfile:1

# Build stage: install API extras using cached wheels
FROM sidetrack-base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --find-links /wheels 'sidetrack[api]'

# Runtime stage: copy installed packages into a clean base image
FROM sidetrack-base AS runtime
COPY --from=builder /usr/local /usr/local

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "sidetrack.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
