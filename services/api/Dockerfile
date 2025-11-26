# syntax=docker/dockerfile:1

# Build stage: install API extras using cached wheels
FROM sidetrack/base:dev AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
# Install from cached wheels only to avoid PyPI name conflicts
RUN pip install --no-cache-dir --no-index --find-links /wheels \
    'uvicorn[standard]==0.30.1' \
    'sidetrack[api]'
# Verify uvicorn is present to fail fast at build time
RUN python -c "import uvicorn; print('uvicorn OK', uvicorn.__version__)"

# Runtime stage: copy installed packages into a clean base image
FROM sidetrack/base:dev AS runtime
COPY --from=builder /usr/local /usr/local
# Verify installed packages exist in the runtime image
RUN python -c "import sidetrack, uvicorn; print('api runtime deps OK')"

# Provide Alembic config/scripts inside the image for DB migrations
RUN mkdir -p /srv/api
COPY alembic.ini /srv/api/alembic.ini
COPY migrations /srv/api/migrations
# Make the script location absolute in the in-image config
RUN sed -i 's#^script_location\s*=.*#script_location = /srv/api/migrations#' /srv/api/alembic.ini
# Allow running `alembic upgrade head` without specifying -c each time
ENV ALEMBIC_CONFIG=/srv/api/alembic.ini

# Ship the application code used by the FastAPI app factory
COPY apps /app/apps

EXPOSE 8000
CMD [
  "python",
  "-m",
  "uvicorn",
  "apps.api.main:create_app",
  "--factory",
  "--host",
  "0.0.0.0",
  "--port",
  "8000"
]
