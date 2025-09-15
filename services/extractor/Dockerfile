# syntax=docker/dockerfile:1

# Build stage: install extractor extras using cached wheels
FROM sidetrack/base:dev AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --no-index --find-links /wheels 'sidetrack[extractor]'

# Runtime stage: minimal image with ffmpeg and installed packages
FROM sidetrack/base:dev AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local /usr/local
RUN python -c "import sidetrack; print('extraction runtime deps OK')"

CMD ["python", "-m", "sidetrack.extraction", "--schedule", "@daily"]
