FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Working directory for sidetrack package
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install API dependencies
COPY services/api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy and install sidetrack package
COPY sidetrack/ /app/sidetrack/
COPY pyproject.toml /app/
RUN pip install --no-cache-dir /app

EXPOSE 8000
CMD ["uvicorn", "sidetrack.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
