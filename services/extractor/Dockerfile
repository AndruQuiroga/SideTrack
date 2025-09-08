FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY services/extractor/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy and install sidetrack package
COPY pyproject.toml sidetrack /app/
RUN pip install /app

# Run extractor
CMD ["python", "-m", "sidetrack.extractor.run", "--schedule", "@daily"]
