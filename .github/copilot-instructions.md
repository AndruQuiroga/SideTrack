# Copilot Instructions for Sidetrack

## Project Overview

Sidetrack is a monorepo combining a **Discord album club bot**, a **public web archive**, and a **social music tracking platform**. Read `AGENTS.md` for full context and `agents/*.md` for component-specific task specs with IDs (e.g. `api/club-weeks`, `bot/nominations-parser`).

## Architecture

Services talk through a central FastAPI backend:

- **`services/api`** — Python/FastAPI, SQLAlchemy, PostgreSQL. Source of truth for all data.
- **`services/worker`** — Python. Background jobs (RQ + APScheduler) for Spotify/Last.fm sync and taste analysis.
- **`services/extraction`** — Python/FastAPI, GPU. Audio feature extraction (isolated, heavy deps).
- **`apps/bot`** — TypeScript, discord.js. Orchestrates weekly club cycle on Discord, syncs to API.
- **`apps/web`** — Next.js 14, React, TailwindCSS. Public archive + authenticated social UI. Talks only to the API.
- **`packages/api-client`** — Shared TS types (codegen'd from OpenAPI) and API client consumed by bot/web.

Data flows: Discord → Bot → API → DB. Spotify/Last.fm → Worker → DB. Web → API (read).

## Build, Test, and Lint

### Python (API + Worker)

All Python commands use `uv` with locked deps:

```bash
# Shorthand used in Makefile
UV_RUN="uv run --frozen --python 3.11 --extra api --extra dev"

# Lint (ruff + mypy)
make lint

# Format
make format.python

# Run all non-slow tests
make test.all

# Run only unit tests
make test.unit

# Run a single test file or test function
$UV_RUN pytest services/api/path/to/test_file.py -m "unit"
$UV_RUN pytest services/api/path/to/test_file.py::test_function_name

# Run by marker: unit, integration, contract, slow, gpu, e2e
$UV_RUN pytest -m "integration"
```

pytest is configured with `--strict-markers -x` (fail-fast) and excludes `contract` tests by default.

### TypeScript (Bot, Web, API Client)

```bash
# Install deps
pnpm install

# Lint/format/build/test across all TS packages
pnpm lint
pnpm format
pnpm build
pnpm test

# Target a single workspace
pnpm --filter @sidetrack/web run build
pnpm --filter @sidetrack/bot run lint
```

### Docker (primary way to run and test apps)

Use Docker Compose to stand up and test the full stack. Always verify changes by running the apps in containers rather than relying solely on local/host processes.

```bash
docker compose up --build          # All services (db, redis, api, web, bot, worker)
docker compose up --build api web  # Just the services you're working on
docker compose logs -f api         # Tail logs for a specific service
docker compose down                # Stop and remove containers
docker build -f services/api/Dockerfile -t sidetrack/api:dev .  # Build a single image
```

The API is at `http://localhost:8000` and the web app at `http://localhost:3000` once containers are healthy.

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push to `main` and all PRs:

- Python: `uv run` for ruff, mypy, and pytest (no nox)
- TypeScript: `pnpm -r run lint && pnpm -r run test` with `--frozen-lockfile`
- Docker: builds API, bot, and web images

## API Conventions

### Models → Schemas → Routes

The API follows a strict three-layer pattern:

1. **Models** (`services/api/models/`) — SQLAlchemy ORM classes inheriting from `services.api.models.base.Base`. Organized by domain: `user.py`, `music.py`, `club.py`, `listening.py`, `social.py`.
2. **Schemas** (`services/api/schemas/core.py`) — Pydantic v2 models for request/response validation. Follow `{Entity}Base` / `{Entity}Create` / `{Entity}Read` naming. All schemas inherit from `OrmSchema` (which sets `model_config = ConfigDict(from_attributes=True)`).
3. **Routes** (`services/api/routes/`) — One file per resource. Each exports a `router` that gets registered in `routes/__init__.py` → `register_routes()`.

When adding a new entity: add the model, create schemas, add a route file, and register it in `routes/__init__.py`.

### Database & Migrations

- Alembic manages migrations in `migrations/versions/`.
- `migrations/env.py` imports `services.api.models.all_metadata` to detect model changes.
- `DATABASE_URL` env var drives both the API and Alembic (uses `postgresql+psycopg://` driver).

### App Factory

The API uses a factory pattern: `services.api.main:create_app`. Run locally with:

```bash
uvicorn services.api.main:create_app --factory --reload
```

### Configuration

Settings are loaded via `pydantic-settings` (`services/api/config.py`) from environment variables and `.env`. Use `get_settings()` (cached) to access them.

## Code Style

- **Python**: Ruff handles all linting and formatting (line-length 100, Python 3.11 target). Mypy for type checking. No black or isort — ruff replaces both. Pre-commit hooks enforce ruff and prettier.
- **TypeScript**: ESLint 9 (flat config in `eslint.config.mjs`) + Prettier (printWidth 100, single quotes, trailing commas, semicolons). Base tsconfig at repo root (ES2022 target); each app extends it.
- Prefer small, focused modules and typed interfaces for all API contracts.

## Environment Setup

Copy `.env.example` to `.env`. Key vars documented in `config/ENVIRONMENT.md`. Never commit secrets — all sensitive values come from env vars.

## Agent Task Specs

Task documents in `agents/` contain structured work items with IDs, goals, steps, and acceptance criteria:

- `agents/api.md` — API endpoints and data model tasks
- `agents/bot.md` — Discord bot orchestration
- `agents/web.md` — Frontend archive and social UI
- `agents/worker.md` — Background sync and analysis jobs
- `agents/data-model.md` — Canonical schema and migration tasks
- `agents/core.md` — Infra, monorepo, Docker, CI

Reference task IDs in commits (e.g. `api/schema-club`). Update the relevant `agents/*.md` when adding new models or endpoints.
