# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python (API + Worker)

All Python commands run through `uv` with the locked environment:

```bash
# Install / sync deps
uv sync --python 3.11 --extra api --extra dev

# Lint (ruff + mypy)
make lint
# or: uv run --frozen --python 3.11 --extra api --extra dev ruff check services/api

# Format
make format.python

# Run tests
make test.unit          # unit tests only (fast, no external services)
make test.int           # integration tests
make test.all           # all except slow/gpu/contract

# Run a single test file or function
uv run --frozen --python 3.11 --extra api --extra dev pytest services/api/path/to/test_file.py
uv run --frozen --python 3.11 --extra api --extra dev pytest services/api/path/to/test_file.py::test_function_name

# Database migrations
uv run --frozen --extra api alembic upgrade head
```

pytest runs with `--strict-markers -x` (fail-fast) and excludes `contract` tests by default. Markers: `unit`, `integration`, `contract`, `slow`, `gpu`, `e2e`.

### TypeScript (Bot, Web, API Client)

```bash
pnpm install            # install all workspace deps

pnpm lint               # lint all packages
pnpm format             # format all packages
pnpm build              # build all packages
pnpm test               # test all packages

# Target a single workspace
pnpm --filter @sidetrack/web run build
pnpm --filter @sidetrack/bot run lint
pnpm --filter @sidetrack/web run dev

# Web UI tests specifically
make test-ui            # runs lint + jest in apps/web
```

### Docker

```bash
docker compose up --build          # all services
docker build -f services/api/Dockerfile -t sidetrack/api:dev .
```

### Run API locally (without Docker)

```bash
uvicorn services.api.main:create_app --factory --reload
```

## Architecture

Sidetrack is a monorepo. All services communicate through the central FastAPI backend — no service talks directly to the database except the API and the worker.

**Data flows:**

- Discord → `apps/bot` → `services/api` → PostgreSQL
- Spotify/Last.fm → `services/worker` → PostgreSQL (direct DB access)
- Browser → `apps/web` → `services/api` (read/write)

### Services

| Service               | Language                        | Purpose                                                    |
| --------------------- | ------------------------------- | ---------------------------------------------------------- |
| `services/api`        | Python / FastAPI / SQLAlchemy   | Single source of truth; all DB access goes here            |
| `services/worker`     | Python / RQ + APScheduler       | Spotify/Last.fm sync, taste analysis, background jobs      |
| `apps/bot`            | TypeScript / discord.js         | Weekly club cycle automation; syncs to API                 |
| `apps/web`            | TypeScript / Next.js / Tailwind | Public archive + authenticated social UI                   |
| `packages/api-client` | TypeScript                      | Codegen'd types + typed API client shared by bot/web       |
| `services/extraction` | Python / FastAPI / librosa      | GPU-heavy audio feature extraction (standalone, see below) |

### Web App Convention (apps/web)

Next.js App Router layout. Pages live in `app/`, components in `app/components/`, API helpers and config in `app/lib/` (specifically `app/lib/api/`, `app/lib/auth.ts`, `app/lib/config.ts`). There is no `src/` directory.

### API Layer Pattern (services/api)

The API strictly follows a three-layer pattern:

1. **Models** (`services/api/models/`) — SQLAlchemy ORM classes inheriting from `services.api.models.base.Base`. Organized by domain: `user.py`, `music.py`, `club.py`, `listening.py`, `social.py`.
2. **Schemas** (`services/api/schemas/core.py`) — Pydantic v2. Naming: `{Entity}Base` / `{Entity}Create` / `{Entity}Read`. All inherit from `OrmSchema` (sets `model_config = ConfigDict(from_attributes=True)`).
3. **Routes** (`services/api/routes/`) — One file per resource, each exporting a `router`. Registered in `routes/__init__.py` → `register_routes()`.

When adding a new entity: add the model, create schemas, add a route file, register it in `routes/__init__.py`.

The app uses a factory pattern: `services.api.main:create_app`. Settings are loaded via `pydantic-settings` from `services/api/config.py` using `get_settings()` (LRU-cached).

### Database & Migrations

- Alembic manages migrations in `migrations/versions/`.
- `migrations/env.py` imports `services.api.models.all_metadata` to detect model changes.
- `DATABASE_URL` must use the `postgresql+psycopg://` driver for both the API and Alembic.

### Shared TypeScript Package

`packages/api-client` exports a typed API client (codegen'd from OpenAPI spec) and TypeScript interfaces. Bot and web import from `@sidetrack/api-client`.

## Package Management

- **Python**: Use `uv` exclusively — never `pip install` or `python -m venv`. Lockfile is `uv.lock` (checked in, do not edit by hand). Build backend is `hatchling`. Target Python 3.11 (3.12+ currently avoided).
- **TypeScript**: Use `pnpm` exclusively — never `npm` or `yarn`. Lockfile is `pnpm-lock.yaml` (checked in). Workspace config is `pnpm-workspace.yaml`.

### Heavy / GPU Dependency Isolation

**Never add heavy ML/GPU packages** (tensorflow, librosa, openl3, scipy, torch, etc.) to the root `pyproject.toml`. uv resolves ALL optional extras into a single lockfile — even if you only install `--extra api`, the lock step must resolve every extra, making it slow and fragile for everyone.

Instead, heavy workloads live as **standalone Python projects** under `services/`:

```
services/
  extraction/           # GPU audio analysis — own pyproject.toml + uv.lock
    pyproject.toml
    uv.lock
    Dockerfile          # nvidia/cuda base
    src/extraction/
```

These services are NOT uv workspace members (workspaces share lockfiles). They communicate with the API over HTTP and deploy independently. Use `docker compose --profile gpu up extraction` to run locally.

See `services/extraction/README.md` for the full pattern.

## Code Style

- **Python**: Ruff handles all linting and formatting (line-length 100, py311 target) + mypy for type checking. No black or isort — ruff replaces both. Migrations in `migrations/versions/` are excluded from linting.
- **TypeScript**: ESLint 9 (flat config in `eslint.config.mjs`) + Prettier (printWidth 100, single quotes, trailing commas, semicolons). Base tsconfig at `tsconfig.base.json` (ES2022 target); each app extends it.

## Agent Task Specs

Structured work items with IDs, goals, steps, and acceptance criteria live in `agents/*.md`:

- `agents/api.md` — API endpoints and data model tasks
- `agents/bot.md` — Discord bot orchestration
- `agents/web.md` — Frontend archive and social UI
- `agents/worker.md` — Background sync and analysis jobs
- `agents/analysis.md` — Taste profiling, similarity, recommendations
- `agents/data-model.md` — Canonical schema and migration tasks
- `agents/core.md` — Infra, monorepo, Docker, CI
- `agents/refactor-tracker.md` — Architecture refactor roadmap and progress tracker

Reference task IDs in commits (e.g. `api/schema-club`). Update the relevant `agents/*.md` when adding new models or endpoints.

## Environment

Copy `.env.example` to `.env`. Key variables:

- `DATABASE_URL` — uses `postgresql+psycopg://` syntax
- `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_CLIENT_ID`
- `SIDETRACK_API_TOKEN` — shared secret for bot/worker → API auth
- `NEXT_PUBLIC_API_BASE_URL` / `SIDETRACK_API_BASE_URL` — API host for web/bot
- `LASTFM_API_KEY`, `LASTFM_API_SECRET`

Full variable reference: `config/ENVIRONMENT.md`.
