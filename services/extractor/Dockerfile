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

# Copy monorepo services to ensure imports resolve
COPY services /src/services
ENV PYTHONPATH=/src

# Run extractor from source
WORKDIR /src/services/extractor
CMD ["python","-m","extractor.run","--schedule","@daily"]
