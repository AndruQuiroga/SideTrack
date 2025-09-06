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

# Make shared models importable
COPY services/common /src/services/common
ENV PYTHONPATH=/src:/app

# App code
COPY services/extractor/extractor /app/extractor

CMD ["python","-m","extractor.run","--schedule","@daily"]
