# Dockerfile
FROM timescale/timescaledb-ha:pg16

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-pgvector \
 && rm -rf /var/lib/apt/lists/*

# back to the default runtime user
USER postgres