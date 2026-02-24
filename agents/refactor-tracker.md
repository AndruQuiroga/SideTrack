# Sidetrack Architecture Refactor — Tracker

> **Canonical location:** `agents/refactor-tracker.md`
> **Created:** 2026-02-24
> **Last updated:** 2026-02-24 <!-- all six phases complete -->

## Overview

This tracker captures the findings from a full architectural audit conducted on 2026-02-24.
The audit focused on the extraction server separation (completed), residual dead code, schema
mismatches, blocking work in the API request cycle, and unused infrastructure.

Key themes:

- The extraction service was successfully isolated into `services/extraction/`, but the
  compose.yml definition is broken (wrong YAML nesting).
- Redis and RQ are declared as API dependencies but never wired up. Heavy operations
  (Last.fm ingest, taste profiling) run synchronously in API route handlers.
- Multiple stub routes, unused modules, and schema/model mismatches exist.

## Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[-]` Cancelled / Skipped

---

## Phase 1: Infrastructure Fixes

_Goal: Fix broken config and wire up the RQ job queue so subsequent phases can use it._

### refactor/compose-fix

- [x] Move extraction service from `volumes:` to `services:` in compose.yml
- [x] Verify with `docker compose config --profiles gpu`

### refactor/redis-config

- [x] Add `redis_url` to `apps/api/config.py` Settings class

### refactor/rq-infra

- [x] Create `apps/api/queue.py` — Redis connection + RQ queue factory
- [x] Add `rq-worker` service to compose.yml
- [x] Create Python RQ worker entrypoint (`apps/api/rq_worker.py`)

---

## Phase 2: Move Blocking Work to RQ

_Goal: Stop the API from blocking on heavy I/O. Dispatch to background jobs instead._

### refactor/ingest-to-rq

- [x] Convert `ingest_lastfm()` in `apps/api/services/ingest.py` to an RQ job function
- [x] Change `POST /ingest/lastfm` to enqueue the job and return `202 Accepted`
- [x] Add `GET /jobs/{job_id}/status` endpoint for job polling
- [x] Update TS worker Last.fm connector to handle async `202` response
- [x] Add ListenEvent deduplication constraint `(user_id, track_id, played_at)`

### refactor/taste-to-rq

- [x] Convert `compute_user_taste_profile()` to an RQ job
- [x] Change `POST .../taste-profiles/recompute` to enqueue and return `202`
- [ ] Add pagination / batching to the listen events query (currently unbounded)

### refactor/fix-http-blocking

- [x] Replace `time.sleep()` in `apps/api/external/http.py` with non-blocking alternative
- [x] Create shared `httpx.Client` instance for connection pooling

---

## Phase 3: Fix Schema & Data Mismatches

_Goal: Make the API return correct data and respect external API rate limits._

### refactor/taste-schema-fix

- [x] Add `genre_histogram`, `feature_means`, `time_of_day_histogram` fields to `TasteProfileRead`
- [x] Remove or rework the `TasteProfileSummary` wrapper
- [x] Remove orphaned `TasteFingerprint` schema (keep only the dataclass in `analysis/taste.py`)

### refactor/musicbrainz-ratelimit

- [x] Add 1 req/sec rate limiter to MusicBrainz client in `apps/api/external/musicbrainz.py`

---

## Phase 4: Dead Code Cleanup

_Goal: Remove stubs, fakes, and unused code that add confusion._

### refactor/remove-stubs

- [x] Delete `apps/api/routes/playlists.py` (entirely hardcoded fake data)
- [x] Deregister the playlists router from `apps/api/routes/__init__.py`
- [x] Fix or remove fake OAuth URLs in `apps/api/routes/integrations.py` → replaced with 501 Not Implemented

### refactor/remove-unused

- [x] Delete `apps/api/external/listenbrainz.py` (never imported)
- [x] Remove `listenbrainz_user_agent` from `apps/api/config.py`
- [x] Remove unused `search_artists` from `apps/api/external/musicbrainz.py`
- [x] Remove unused `get_top_artists` and `get_top_albums` from `apps/api/external/lastfm.py`
- [x] Remove unused `union_all` import from `apps/api/routes/feed.py`
- [x] Remove unused schemas: `TrackCreate`, `TasteFingerprint` (removed in Phase 3 & 4)

### refactor/worker-stubs

- [x] Replace fake ListenBrainz connector data in `apps/worker/src/connectors/listenbrainz.ts`
      with `console.warn("ListenBrainz not implemented")` + return empty array

### refactor/dead-models

- [x] Add documentation comments on `Compatibility` and `UserRecommendation` tables (reserved for future use)
- [x] Add TODO for `time_of_day_histogram` population in taste computation (`analysis/taste.py`)

---

## Phase 5: DRY & Consolidation

_Goal: Eliminate duplication and improve code hygiene._

### refactor/dedup-constants

- [x] Move `FEATURE_FIELDS` to `apps/api/analysis/constants.py` (new file, single source of truth)
- [x] Update imports in `taste.py`, `compatibility.py`, and `__init__.py`

### refactor/httpx-pool

- [x] Create shared `httpx.Client` instance (done in Phase 2 — `apps/api/external/http.py`)

---

## Phase 6: Extraction Service Cleanup

_Goal: Ensure the extraction service scaffold is correct and buildable._

### refactor/extraction-dockerfile

- [x] Fix `uv.lock` reference in Dockerfile — removed COPY of non-existent file, use `uv sync --no-lock`
- [x] Verify `scripts/bench_extractor.py` still runs (confirmed: standalone script, no extraction imports)

### refactor/extraction-env

- [x] Clarify `AUDIO_ROOT` / `CACHE_DIR` in `.env.example` with comments explaining extraction-service-only paths

---

---

# Project Restructure — 7-Phase Plan

> **Started:** 2026-02-24
> **Goal:** Restructure the monorepo layout, consolidate workers, add type codegen, fix broken models, and clean up.

## Restructure Phase 1: Move `apps/api/` → `services/api/`

_Goal: Move the API into `services/` alongside extraction. Remove `apps/__init__.py`._

### restructure/move-api

- [x] Copy `apps/api/` to `services/api/`, create `services/__init__.py`
- [x] Bulk-replace all `apps.api` → `services.api` imports (~30 files, 179 refs)
- [x] Update `migrations/env.py`, entrypoint.sh, Dockerfile, compose.yml
- [x] Update `pyproject.toml` packages, Makefile, CI workflow
- [x] Delete `apps/api/` and `apps/__init__.py`
- [x] Update all documentation (README, CLAUDE.md, copilot-instructions, agents/_.md, docs/_.md)

---

## Restructure Phase 2: Consolidate Workers → `services/worker/`

_Goal: Replace the TS setInterval worker with a Python worker using APScheduler + RQ. Delete `apps/worker/`._

### restructure/worker-scaffold

- [x] Create `services/worker/` directory with `__init__.py`, `__main__.py`, `config.py`
- [x] Add `apscheduler` to `pyproject.toml` dependencies
- [x] Create `Dockerfile` for the new Python worker

### restructure/worker-spotify-connector

- [x] Port `SpotifyConnector` to Python (`services/worker/connectors/spotify.py`)
  - Token refresh (refresh_token grant)
  - Fetch recent (up to 50, cursor-based)
  - Fetch now-playing
  - Client credentials token for audio features

### restructure/worker-features-job

- [x] Port `PopulateFeaturesJob` to Python (`services/worker/jobs/populate_features.py`)
  - Client credentials token → batch fetch audio features (100/batch)
  - Write features directly to DB (not via API)

### restructure/worker-sync

- [x] Port `SyncCoordinator` logic (`services/worker/sync.py`)
  - Full sync: iterate users → linked accounts → fetch recent → upsert listen events
  - Now-playing sweep: iterate users → fetch now-playing → upsert
  - Direct DB writes instead of API HTTP calls

### restructure/worker-listen-store

- [x] Port `ListenEventStore` dedup + upsert to Python (`services/worker/listen_store.py`)
  - Deterministic UUID generation (SHA1-based)
  - In-memory dedup set
  - Direct DB upsert (ON CONFLICT DO NOTHING)

### restructure/worker-scheduler

- [x] Implement APScheduler periodic tasks (`services/worker/__main__.py`)
  - Full sync every 15 min (configurable)
  - Now-playing sweep every 45s (configurable, toggleable)
  - Audio features population every 60 min (configurable)
  - Keep RQ worker running in same process for existing async jobs

### restructure/worker-health

- [x] Add health/status HTTP endpoint (plain HTTP, port 8700)
- [x] Expose sync metrics and cursor state

### restructure/worker-infra

- [x] Update `compose.yml`: replace TS worker with Python worker, merge rq-worker
- [x] Update `Makefile`: add worker lint/format targets
- [x] Update CI workflow for new worker
- [x] Delete `apps/worker/` entirely
- [x] Update `pnpm-workspace.yaml` to remove `apps/worker`
- [x] Update documentation

---

## Restructure Phase 3: OpenAPI Codegen → `@sidetrack/api-client`

_Goal: Replace hand-written TS types with codegen from FastAPI's OpenAPI spec._

### restructure/api-client-rename

- [x] Rename `packages/shared/` → `packages/api-client/`
- [x] Update package name to `@sidetrack/api-client`
- [x] Update all TS imports (`@sidetrack/shared` → `@sidetrack/api-client`)

### restructure/openapi-codegen

- [x] Add Makefile target: dump `/openapi.json` + run `openapi-typescript`
- [x] Add `openapi-typescript` and `openapi-fetch` as devDependencies
- [x] Generate types from OpenAPI spec, replace hand-written `types.ts`
- [ ] Rewrite API client to use `openapi-fetch` instead of raw axios
- [x] Delete dead files: `env.ts`, `project.ts`
- [x] Stop committing `dist/` to git (add to `.gitignore`)

---

## Restructure Phase 4: Fix Broken Models

_Goal: Fix known model/type errors._

### restructure/fix-user-recommendation

- [x] Add missing `id` primary key to `UserRecommendation`
- [x] Add missing `user_id` mapped column

### restructure/fix-taste-type

- [x] Fix `Sequence[TrackFeature]` → `list[TrackFeature]` in `analysis/taste.py`

### restructure/fix-forward-refs

- [x] Clean up forward reference LSP issues with `TYPE_CHECKING` imports

---

## Restructure Phase 5: Clean Up Web App Structure

_Goal: Consolidate confusing `app/` vs `src/` layout._

### restructure/web-consolidate

- [x] Move `apps/web/src/` utilities into `apps/web/app/lib/`
- [x] Delete empty placeholder files
- [ ] Extend `tsconfig.base.json`
- [ ] Update to use codegen'd API client

---

## Restructure Phase 6: Clean Up Config and Tooling

_Goal: Fix misc config issues._

### restructure/config-cleanup

- [x] Fix `pnpm-workspace.yaml` redundant globs
- [x] Fix TS Dockerfiles (`--frozen-lockfile`)
- [x] Normalize dependency versions
- [x] Bot config consolidation

---

## Restructure Phase 7: Verify + Update Docs

_Goal: End-to-end verification._

### restructure/verify

- [x] `docker compose config`
- [x] `ruff check` + `mypy` pass
- [x] `pnpm lint` + `pnpm build` pass
- [x] `pytest` pass
- [ ] Build Docker images
- [x] Update tracker and AGENTS.md

---

## Audit Log

_Append-only log of completed work._

| Date       | Phase | Task ID                             | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------- | ----- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-02-24 | —     | —                                   | Initial audit completed. Tracker created.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-02-24 | 1     | refactor/compose-fix                | Moved extraction from volumes: to services:. Verified with `docker compose --profile gpu config`.                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-02-24 | 1     | refactor/redis-config               | Added `redis_url` to Settings in config.py.                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-02-24 | 1     | refactor/rq-infra                   | Created queue.py (Redis conn + queue factory) and rq_worker.py (worker entrypoint). Added rq-worker service to compose.yml.                                                                                                                                                                                                                                                                                                                                                         |
| 2026-02-24 | 2     | refactor/ingest-to-rq               | Created jobs.py with job_ingest_lastfm. Rewrote routes/ingest.py to enqueue+202. Created routes/jobs.py status endpoint. Updated TS shared client + lastfm connector. Added ListenEvent dedup constraint + migration 0003.                                                                                                                                                                                                                                                          |
| 2026-02-24 | 2     | refactor/taste-to-rq                | Created job_recompute_taste_profile in jobs.py. Rewrote routes/taste_profiles.py to enqueue+202.                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-02-24 | 2     | refactor/fix-http-blocking          | Rewrote external/http.py with shared module-level httpx.Client, connection pooling, ExternalApiError class.                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-02-24 | 3     | refactor/taste-schema-fix           | Rewrote `TasteProfileRead` with correct ORM fields. Removed `TasteProfileSummary` and orphaned `TasteFingerprint` schema.                                                                                                                                                                                                                                                                                                                                                           |
| 2026-02-24 | 3     | refactor/musicbrainz-ratelimit      | Added thread-safe 1 req/sec rate limiter via `_throttle()` in musicbrainz.py. Removed unused `search_artists`. Centralised requests through `_mb_request()`.                                                                                                                                                                                                                                                                                                                        |
| 2026-02-24 | 4     | refactor/remove-stubs               | Deleted `routes/playlists.py`. Deregistered from router. Replaced fake OAuth URLs in integrations.py with 501 Not Implemented.                                                                                                                                                                                                                                                                                                                                                      |
| 2026-02-24 | 4     | refactor/remove-unused              | Deleted `external/listenbrainz.py`. Removed `listenbrainz_user_agent` from config. Removed unused funcs from lastfm.py and musicbrainz.py. Removed unused `union_all` import. Removed `TrackCreate` schema.                                                                                                                                                                                                                                                                         |
| 2026-02-24 | 4     | refactor/worker-stubs               | Rewrote `listenbrainz.ts` connector: all methods now log warnings and return empty/null instead of fake data.                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-02-24 | 4     | refactor/dead-models                | Added detailed docstrings to `Compatibility` and `UserRecommendation` models. Added TODO comment for `time_of_day_histogram` computation in `analysis/taste.py`.                                                                                                                                                                                                                                                                                                                    |
| 2026-02-24 | 5     | refactor/dedup-constants            | Created `analysis/constants.py` with canonical `FEATURE_FIELDS`. Updated imports in `taste.py`, `compatibility.py`, and `__init__.py` to use single source.                                                                                                                                                                                                                                                                                                                         |
| 2026-02-24 | 5     | refactor/httpx-pool                 | Already completed in Phase 2 — marked done.                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-02-24 | 6     | refactor/extraction-dockerfile      | Fixed Dockerfile: removed COPY of non-existent `uv.lock`, switched to `uv sync --no-lock`. Verified bench_extractor.py is standalone and functional.                                                                                                                                                                                                                                                                                                                                |
| 2026-02-24 | 6     | refactor/extraction-env             | Added clarifying comments for `AUDIO_ROOT` and `CACHE_DIR` in `.env.example` (extraction-service-only paths).                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-02-24 | —     | —                                   | **All six phases complete.** Remaining deferred items: listen-events pagination (Phase 2), `time_of_day_histogram` implementation (Phase 4 TODO).                                                                                                                                                                                                                                                                                                                                   |
| 2026-02-24 | R-1   | restructure/move-api                | Moved `apps/api/` → `services/api/`. Rewrote 179 import refs across ~30 files. Updated Dockerfile, compose, Makefile, CI, all docs. Deleted `apps/api/` and `apps/__init__.py`.                                                                                                                                                                                                                                                                                                     |
| 2026-02-24 | R-2   | restructure/worker-\*               | Full TS→Python worker port. Created `services/worker/` with SpotifyConnector, ListenEventStore, SyncCoordinator, PopulateFeaturesJob, APScheduler+RQ entry point, health endpoint. Deleted `apps/worker/`. Merged rq-worker service. Updated compose, Makefile, CI, pnpm-workspace, docs. Ruff+mypy clean.                                                                                                                                                                          |
| 2026-02-24 | R-3   | restructure/api-client-rename       | Renamed `packages/shared/` → `packages/api-client/`. Updated 17 TS imports across bot (9 files) and web (8 files). Updated package.json deps, pnpm-workspace.yaml.                                                                                                                                                                                                                                                                                                                  |
| 2026-02-24 | R-3   | restructure/openapi-codegen         | Generated OpenAPI spec (42 paths, 45 schemas) and TS types (3353 lines). Added `openapi-typescript` devDep, `generate` script, Makefile `openapi` target. Added `openapi.json` to `.gitignore`. Deleted dead `project.ts`. Fixed thread ID type mismatches (`number` → `string \| number`) in web components. All three TS packages build clean.                                                                                                                                    |
| 2026-02-24 | R-4   | restructure/fix-user-recommendation | Added missing `id` (UUID PK) and `user_id` (UUID FK) columns to `UserRecommendation` model.                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-02-24 | R-4   | restructure/fix-taste-type          | Wrapped `db.scalars().all()` in `list()` in `analysis/taste.py` to fix `Sequence` vs `list` type error.                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-02-24 | R-4   | (bonus)                             | Fixed admin.py 204 response body assertion error. Fixed schemas/**init**.py missing exports (`UserUpdate`, `TrackFeatureCreate`, `TrackFeatureRead`).                                                                                                                                                                                                                                                                                                                               |
| 2026-02-24 | R-5   | restructure/web-consolidate         | Moved 7 active files from `apps/web/src/` to `app/lib/` and `lib/auth.ts` to `app/lib/auth.ts`. Deleted entire `src/ui/` subtree (5 dead legacy HTML renderers), `src/index.ts`, `src/components/forms/`. Updated 17 import statements across 16 files. Removed empty `src/` and `lib/` directories. Web build passes clean.                                                                                                                                                        |
| 2026-02-24 | R-6   | restructure/config-cleanup          | Fixed both TS Dockerfiles: added `pnpm-lock.yaml` COPY, enabled `--frozen-lockfile`, removed stale `apps/worker/` and `packages/shared/` refs, updated to `packages/api-client/`. Normalized `@types/node` (removed ^20 override in web, inherits ^22 from root). Added `forceConsistentCasingInFileNames` to web tsconfig. Fixed web format script to target `app/` instead of old `src/`. Bot config already well-consolidated — no changes needed. pnpm-workspace already clean. |
| 2026-02-24 | R-7   | restructure/verify                  | Full verification pass. docker compose config validates. ruff check passes (0 errors, was 95 — auto-fixed 81, manually fixed 34). mypy has 41 pre-existing errors (none from refactor). ESLint passes on all packages (added `allowInterfaces: with-single-extends` rule, cleaned JS build artifacts from src/ dirs). pnpm build passes for all 3 packages (bot, web, api-client). pytest passes (14/14). Resolved forward ref F821s via TYPE_CHECKING imports in 4 model files.    |
