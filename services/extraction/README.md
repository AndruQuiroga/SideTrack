# Sidetrack Extraction Service

Standalone microservice for GPU-heavy audio feature extraction (librosa, openl3, tensorflow).

## Why Standalone?

This service has its own `pyproject.toml` and `uv.lock` because:

1. **uv resolves ALL optional extras into a single lockfile.** Putting heavy deps as an extra in the root `pyproject.toml` would force every developer and CI run to resolve tensorflow, keras, CUDA bindings, etc. — even when they only work on the API or web frontend.
2. **uv workspace members also share a lockfile.** So this is NOT a uv workspace member.
3. **GPU workloads need separate deployment.** This service runs on GPU-capable nodes while the main API runs on cheap CPU instances.

## Architecture

```
Browser / Bot
       │
       ▼
  services/api  ◄────►  PostgreSQL
       │
       ▼ (HTTP)
services/extraction   ← YOU ARE HERE
```

The extraction service:

- Receives requests from the API (e.g., "extract features for track X")
- Downloads audio, runs librosa/openl3 analysis
- Returns feature vectors back to the API for storage

## Development

```bash
cd services/extraction

# Install deps (first time)
uv sync --python 3.11

# Run locally
uv run uvicorn extraction.app:app --reload --port 8800

# Run with Docker (GPU)
docker compose --profile gpu up extraction
```

## Adding New Heavy Dependencies

Add them here in `services/extraction/pyproject.toml`, **never** in the root `pyproject.toml`.

```bash
cd services/extraction
uv add some-heavy-package
```
