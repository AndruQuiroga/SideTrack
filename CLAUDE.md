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
# or: uv run --frozen --python 3.11 --extra api --extra dev ruff check apps/api apps/worker

# Format
make format.python

# Run tests
make test.unit          # unit tests only (fast, no external services)
make test.int           # integration tests
make test.all           # all except slow/gpu/contract

# Run a single test file or function
uv run --frozen --python 3.11 --extra api --extra dev pytest apps/api/path/to/test_file.py
uv run --frozen --python 3.11 --extra api --extra dev pytest apps/api/path/to/test_file.py::test_function_name

# Database migrations
uv run --frozen --extra api alembic upgrade head
```

pytest runs with `--strict-markers -x` (fail-fast) and excludes `contract` tests by default. Markers: `unit`, `integration`, `contract`, `slow`, `gpu`, `e2e`.

### TypeScript (Bot, Web, Worker, Shared)

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
docker build -f apps/api/Dockerfile -t sidetrack/api:dev .
```

### Run API locally (without Docker)

```bash
uvicorn apps.api.main:create_app --factory --reload
```

## Architecture

Sidetrack is a monorepo. All services communicate through the central FastAPI backend — no service talks directly to the database except the API.

**Data flows:**

- Discord → `apps/bot` → `apps/api` → PostgreSQL
- Spotify/Last.fm → `apps/worker` → `apps/api` → PostgreSQL
- Browser → `apps/web` → `apps/api` (read/write)

### Services

| App               | Language                        | Purpose                                                                  |
| ----------------- | ------------------------------- | ------------------------------------------------------------------------ |
| `apps/api`        | Python / FastAPI / SQLAlchemy   | Single source of truth; all DB access goes here                          |
| `apps/bot`        | TypeScript / discord.js         | Weekly club cycle automation; syncs to API                               |
| `apps/web`        | TypeScript / Next.js / Tailwind | Public archive + authenticated social UI                                 |
| `apps/worker`     | TypeScript                      | Spotify/Last.fm sync; taste analysis batch jobs                          |
| `packages/shared` | TypeScript                      | Typed interfaces + `SidetrackApiClient` (Axios) shared by bot/web/worker |

### API Layer Pattern (apps/api)

The API strictly follows a three-layer pattern:

1. **Models** (`apps/api/models/`) — SQLAlchemy ORM classes inheriting from `apps.api.models.base.Base`. Organized by domain: `user.py`, `music.py`, `club.py`, `listening.py`, `social.py`.
2. **Schemas** (`apps/api/schemas/core.py`) — Pydantic v2. Naming: `{Entity}Base` / `{Entity}Create` / `{Entity}Read`. All inherit from `OrmSchema` (sets `model_config = ConfigDict(from_attributes=True)`).
3. **Routes** (`apps/api/routes/`) — One file per resource, each exporting a `router`. Registered in `routes/__init__.py` → `register_routes()`.

When adding a new entity: add the model, create schemas, add a route file, register it in `routes/__init__.py`.

The app uses a factory pattern: `apps.api.main:create_app`. Settings are loaded via `pydantic-settings` from `apps/api/config.py` using `get_settings()` (LRU-cached).

### Database & Migrations

- Alembic manages migrations in `migrations/versions/`.
- `migrations/env.py` imports `apps.api.models.all_metadata` to detect model changes.
- `DATABASE_URL` must use the `postgresql+psycopg://` driver for both the API and Alembic.

### Shared TypeScript Package

`packages/shared` exports `SidetrackApiClient` (Axios-based) and typed interfaces mirroring the FastAPI schemas. Bot, web, and worker import from `@sidetrack/shared`.

## Package Management

- **Python**: Use `uv` exclusively — never `pip install` or `python -m venv`. Lockfile is `uv.lock` (checked in, do not edit by hand). Target Python 3.11 (3.12+ currently avoided).
- **TypeScript**: Use `pnpm` exclusively — never `npm` or `yarn`. Workspace config is `pnpm-workspace.yaml`.

## Code Style

- **Python**: Ruff (line-length 100, py311 target) + mypy. Migrations in `migrations/versions/` are excluded from linting.
- **TypeScript**: ESLint + Prettier (printWidth 100, single quotes, trailing commas, semicolons). Base tsconfig at `tsconfig.base.json`; each app extends it.

## Agent Task Specs

Structured work items with IDs, goals, steps, and acceptance criteria live in `agents/*.md`:

- `agents/api.md` — API endpoints and data model tasks
- `agents/bot.md` — Discord bot orchestration
- `agents/web.md` — Frontend archive and social UI
- `agents/worker.md` — Background sync and analysis jobs
- `agents/data-model.md` — Canonical schema and migration tasks
- `agents/core.md` — Infra, monorepo, Docker, CI

Reference task IDs in commits (e.g. `api/schema-club`). Update the relevant `agents/*.md` when adding new models or endpoints.

## Environment

Copy `.env.example` to `.env`. Key variables:

- `DATABASE_URL` — uses `postgresql+psycopg://` syntax
- `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_CLIENT_ID`
- `SIDETRACK_API_TOKEN` — shared secret for bot/worker → API auth
- `NEXT_PUBLIC_API_BASE_URL` / `SIDETRACK_API_BASE_URL` — API host for web/bot/worker
- `LASTFM_API_KEY`, `LASTFM_API_SECRET`

Full variable reference: `config/ENVIRONMENT.md`.
