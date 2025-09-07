FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Working directory for API package (contains alembic.ini)
WORKDIR /srv/api

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy sidetrack package
COPY sidetrack/ /srv/api/sidetrack/

# Copy API sources (package, alembic, config)
COPY services/api/ /srv/api/

# Install API Python package
RUN pip install --no-cache-dir /srv/api

# Make shared models importable (services.common.*)
COPY services/common /src/services/common
ENV PYTHONPATH=/src

EXPOSE 8000
CMD ["uvicorn", "sidetrack.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
