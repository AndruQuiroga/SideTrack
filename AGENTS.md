# Sidetrack: agent instructions

Shared by Codex, Claude Code and any other agent. Keep this file short; details live in the linked docs.

## Read first

1. `docs/STATUS.md`: what actually works today. Trust it over any other prose. It's generated: edit `docs/status.yaml`, then run `python scripts/gen_status.py` (CI fails if it's stale). Marking something **works** requires an evidence path, preferably a test.
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

| Path                  | What                                                                      |
| --------------------- | ------------------------------------------------------------------------- |
| `sidetrack/`          | Canonical Python package; ownership and boundaries in docs/MODULES.md     |
| `services/api`        | Compatibility imports, API tests and image/startup files                  |
| `services/worker`     | Legacy sync worker: not built or deployed, due for replacement (ADR 0002) |
| `services/extraction` | Stub only; the audio lab replaces it                                      |
| `apps/bot`            | discord.js club bot                                                       |
| `apps/web`            | Next.js site                                                              |
| `packages/api-client` | Generated TS client for bot and web                                       |
| `migrations/`         | Alembic                                                                   |
| `deploy/`             | Swarm stack for Stache-Rack (ADR 0006)                                    |

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

Run `uv run --frozen --extra api --extra dev lint-imports` after Python changes.
Domain packages expose public operations and read models; never write another
domain's tables or import its private modules. Legacy adapters must share canonical
objects, especially DB dependencies and queued jobs.

API tests run on Postgres 16 + pgvector: have Docker running (testcontainers starts one), or set `SIDETRACK_TEST_DATABASE_URL` to a throwaway database. A model change needs a migration, or `test_migrations.py` fails.
