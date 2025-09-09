# syntax=docker/dockerfile:1

# Build stage: install worker extras using cached wheels
FROM sidetrack/base:dev AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-index --find-links /wheels 'sidetrack[worker]'

# Runtime stage: copy installed packages into base image
FROM sidetrack/base:dev AS runtime
COPY --from=builder /usr/local /usr/local
RUN python -c "import sidetrack; print('worker runtime deps OK')"

CMD ["python", "-m", "sidetrack.worker.run"]
