# Sidetrack: agent instructions

Shared by Codex, Claude Code and any other agent. Keep this file short; details live in the linked docs.

## Read first

1. `docs/STATUS.md`: what actually works today. Trust it over any other prose.
2. `docs/decisions/`: architecture decisions (ADRs). Don't re-propose a decision without a new ADR.
3. `openspec/specs/`: the behaviour the system must have. `openspec/changes/`: work in flight.

## How work happens

All non-trivial work goes through OpenSpec:

- Claude Code: `/opsx:propose`, `/opsx:apply`, `/opsx:archive`
- Codex: `$openspec-propose`, `$openspec-apply-change`, `$openspec-archive-change`

A bug found mid-task becomes its own change (or a GitHub issue that names the spec it violates), not a silent drive-by fix.

## Hard rules

- **No fakes in production code.** Nothing under `services/`, `apps/` or `packages/` may return placeholder, random or mock data. Unimplemented behaviour raises `NotImplementedError` or reports itself as unavailable. Test doubles live under `tests/` only.
- **No secrets** in code, specs, logs, fixtures or API responses. Config comes from env vars or Docker secrets.
- **No new infrastructure** (Redis, Celery, extra services) without an ADR. Postgres is the only stateful service.
- **Spotify is metadata-only.** Audio features and recommendations are unavailable to this app.
- **yt-dlp is opt-in and personal-only.** Never schedule it and never serve audio over HTTP.

## Layout (current; the target is ADR 0001)

| Path | What |
| --- | --- |
| `services/api` | FastAPI app, SQLAlchemy models, routes |
| `services/worker` | Legacy sync worker, due for replacement (ADR 0002) |
| `services/extraction` | Stub only; the audio lab replaces it |
| `apps/bot` | discord.js club bot |
| `apps/web` | Next.js site |
| `packages/api-client` | Generated TS client for bot and web |
| `migrations/` | Alembic |
| `deploy/` | Swarm stack for Stache-Rack (ADR 0006) |

## Commands

```bash
uv sync --python 3.11 --extra api --extra worker --extra dev   # Python deps
make lint                                                       # ruff + mypy
make test.unit                                                  # fast tests
uv run --frozen --extra api alembic upgrade head                # migrations
pnpm install && pnpm lint && pnpm build                         # TypeScript
pnpm exec openspec list                                         # changes in flight
```

Python: uv only (never pip). TypeScript: pnpm only. Python 3.11. Ruff line length 100.
