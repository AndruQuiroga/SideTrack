FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy project files and install extractor extras
COPY pyproject.toml ./
COPY sidetrack ./sidetrack
RUN pip install --no-cache-dir .[extractor]

# Run extractor
CMD ["python", "-m", "sidetrack.extractor.run", "--schedule", "@daily"]
