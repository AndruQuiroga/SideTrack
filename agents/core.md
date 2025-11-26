# agents/core.md — Monorepo, Env, Infra

## Purpose

Define tasks for setting up and maintaining the **Sidetrack monorepo**, shared configuration, environment management, and basic infrastructure (Docker, local dev scripts, CI hooks). These tasks are largely stack‑agnostic but should align with the architecture described in `AGENTS.md`.

## Context

We want a single repo containing:

- `apps/bot` — Discord bot
- `apps/api` — Backend API
- `apps/web` — Web frontend (Next.js)
- `apps/worker` — Background jobs (sync & analysis)
- `packages/shared` — Shared types, utilities, and SDKs

We prefer a workspace‑friendly package manager such as **pnpm** (for TS parts) and a pattern that plays nicely with Python services (via Docker and shared configs).

---

## Tasks

### core/init-monorepo

**Goal:** Create the repo structure and base tooling to support multiple apps and shared packages.

**Context:**

- We want clear separation of concerns but easy sharing of types and utilities.
- Node/TS parts should share dependencies where possible.
- Python services (API, worker) will be containerized and share a common base image and configuration approach.

**Steps (high level):**

1. Create the folder structure:

   - `apps/bot/`
   - `apps/api/`
   - `apps/web/`
   - `apps/worker/`
   - `packages/shared/`

2. Add workspace support:
   - If using pnpm, create a root `pnpm-workspace.yaml` listing `apps/*` and `packages/*`.
   - Initialize `package.json` at root with scripts like:
     - `dev:web`, `dev:bot`, `dev:worker`.
     - `lint`, `test` as stubs.

3. Add a root `README.md` explaining:
   - Project overview.
   - Structure and how to run each app in dev.

4. Ensure `.gitignore` covers:
   - Node modules, Python venvs, build artifacts, `.env*`.

**Acceptance Criteria:**

- Repo has the described structure.
- `pnpm install` (or chosen manager) at root succeeds.
- Each app directory has a minimal, compilable/bootstrapped project (even if just “hello world”).

---

### core/env-config

**Goal:** Standardize environment configuration and secret management across services.

**Context:**

- We will use environment variables for secrets and per‑env configuration.
- We want a consistent naming scheme and central documentation so agents know what’s available.

**Steps:**

1. Create `config/ENVIRONMENT.md` documenting env vars:
   - `DISCORD_TOKEN`, `DISCORD_GUILD_ID`.
   - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, redirect URIs.
   - `LASTFM_API_KEY`, `LASTFM_SHARED_SECRET`.
   - `DATABASE_URL` for Postgres.
   - `REDIS_URL` for cache/queues.
   - Any `NEXT_PUBLIC_*` vars for frontend.

2. Add small env loader helpers:
   - TS: a tiny `packages/shared/src/env.ts` using a library like `zod` or similar to parse/validate envs.
   - Python: a small `config.py` using `pydantic-settings` or similar.

3. Add `.env.example` at root with placeholders.

**Acceptance Criteria:**

- All services can read their configuration from envs.
- Missing critical envs fail fast with a clear error message.
- `.env.example` is up to date with documented vars.

---

### core/docker-compose

**Goal:** Provide a `docker-compose` setup that spins up all core services and dependencies for local development.

**Context:**

- We need Postgres and Redis.
- We want to be able to run bot, api, web, worker in containers (optional but recommended).

**Steps:**

1. Add `docker-compose.yml` with services:
   - `db`: Postgres (with volume for data).
   - `redis`: Redis (for queues/cache).
   - `api`: builds `apps/api`.
   - `worker`: builds `apps/worker`.
   - `bot`: builds `apps/bot`.
   - `web`: builds `apps/web`.

2. Configure networks, health checks, and environment variables.
3. Optionally add a `Makefile` or npm scripts:
   - `dev:compose-up`
   - `dev:compose-down`

**Acceptance Criteria:**

- `docker compose up` brings up DB and Redis successfully.
- API can connect to DB from inside its container.
- Web can call API via a consistent hostname (e.g., `http://api:8000` inside the network).
- Bot and worker can also reach API and Redis.

---

### core/ci-setup

**Goal:** Provide a minimal CI pipeline that runs tests and basic checks for changed components.

**Context:**

- Likely using GitHub Actions or similar.
- We want to at least run:
  - Web build.
  - API tests.
  - Linting for TS and Python.

**Steps:**

1. Add `.github/workflows/ci.yml`:
   - Node job: install deps, run `lint`, `test`, and web build.
   - Python job: set up Python, install deps, run tests for API and worker.

2. Optionally set up caching for dependencies.

**Acceptance Criteria:**

- CI runs on PRs and main branch.
- Fails clearly when code doesn’t compile, tests fail, or format/lint checks fail.

---

### core/shared-lib-scaffolding

**Goal:** Set up `packages/shared` for shared types and API clients.

**Context:**

- We want bot, web, and worker to share:
  - Type definitions for entities like `Week`, `Nomination`, `Rating`, `ListenEvent`.
  - API client code for calling the backend.

**Steps:**

1. Create `packages/shared/src/` and initialize a TypeScript package.
2. Define base interfaces/types for:
   - User, LinkedAccount, Album, Track, Week, Nomination, Vote, Rating, ListenEvent, TasteProfile.
3. Add a basic HTTP client wrapper:
   - Configurable base URL.
   - Typed methods for common endpoints (even if stubs at first).

**Acceptance Criteria:**

- `packages/shared` builds successfully.
- Bot and web can import basic shared types without circular dependencies.
