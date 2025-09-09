# syntax=docker/dockerfile:1

# Build stage: install scheduler extras using cached wheels
FROM sidetrack-base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --find-links /wheels 'sidetrack[scheduler]'

# Runtime stage: copy installed packages into base image
FROM sidetrack-base AS runtime
COPY --from=builder /usr/local /usr/local
RUN python -c "import sidetrack; print('scheduler runtime deps OK')"

CMD ["python", "-m", "sidetrack.scheduler.run"]
