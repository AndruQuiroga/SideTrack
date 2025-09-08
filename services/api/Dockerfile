FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Working directory for sidetrack package
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files and install API extras
COPY pyproject.toml ./
COPY sidetrack ./sidetrack
RUN pip install --no-cache-dir .[api]

EXPOSE 8000
CMD ["uvicorn", "sidetrack.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
