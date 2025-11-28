# Package Management

Sidetrack now standardizes on **uv** for Python dependencies and **pnpm** for Node/TypeScript workspaces.

## Python (uv)
- Target Python version: **3.11** (see `requires-python` in `pyproject.toml`); 3.12+ is currently avoided because of upstream build breakage.
- Lockfile: `uv.lock` (checked in). Do not edit by hand.
- Create or update the project environment: `uv sync --python 3.11 --extra api --extra dev`
- Run commands through uv so they use the locked env:
  - Lint: `uv run --frozen --extra api --extra dev ruff check apps/api apps/worker`
  - Format: `uv run --frozen --extra api --extra dev ruff format apps/api apps/worker`
  - Types: `uv run --frozen --extra api --extra dev mypy apps/api apps/worker`
  - Tests: `uv run --frozen --extra api --extra dev pytest -m "unit"`
  - Migrations: `uv run --frozen --extra api alembic upgrade head`
- Containers: `apps/api/Dockerfile` installs dependencies with `uv sync` against `uv.lock`.
- Avoid `pip install`/`python -m venv`; prefer uv-managed environments.

## Node/TypeScript (pnpm)
- Workspace manager: `pnpm` (see `packageManager` in `package.json` and `pnpm-workspace.yaml`).
- Install deps: `pnpm install` at the repo root (corepack-enabled Node images already run this in Dockerfiles).
- Run tasks via workspaces:
  - Lint: `pnpm lint` (runs `next lint` in `apps/web`)
  - Format: `pnpm format` (runs Prettier across packages)
  - Tests: `pnpm -r test`, `pnpm --filter @sidetrack/web dev`
- Avoid `npm`/`yarn` to keep the workspace resolution consistent.
