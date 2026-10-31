# Proposal

## Why

Sidetrack has no deployment path to the new homelab. Its CI builds images and throws them away, its env file lists variables nothing reads, and its only deploy artifact is a Caddyfile for a host that no longer exists. Stache-Rack has an established pattern (ADR 0006); Sidetrack should follow it, so it ships the same way the wedding site does.

## What Changes

- CI pushes `ghcr.io/andruquiroga/sidetrack-{api,web,bot}` images on `main` (tags: commit SHA and `main`). Pull requests build without pushing. CI also runs `openspec validate --all --strict`.
- New `deploy/stack.yml`: a Swarm stack for Portainer with Postgres 16 + pgvector, API, web, bot, and the Last.fm ingest worker. Traefik labels on `traefik-public`, bounded logs, healthchecks, node-label placement, `/srv/sidetrack/*` bind mounts.
- Hostnames: `sidetrack.stache.lan` and `api.sidetrack.stache.lan` internally; `sidetrack.network` and `api.sidetrack.network` publicly via the existing Cloudflare Tunnel.
- The API reads settings from env vars or Docker secret files under `/run/secrets`.
- `GET /health` returns 503 when the database is unreachable, so Swarm healthchecks can see it.
- `.env.example` is rewritten to the variables code actually reads; `config/ENVIRONMENT.md` is regenerated to match.
- Removed: `deploy/Caddyfile`, the `services/worker` image and compose service (its Spotify sync is broken and is replaced in Phase 2), and the GPU `extraction` compose profile (a stub).
- Repo settings: branch protection on `main` requiring CI. GHCR packages stay public, matching the public repo (decided 2026-10-25; originally planned private).

### Out of scope

- Replacing Redis and RQ (Phase 2, ADR 0002). Redis stays in the stack until then, with no persistence, because the Last.fm ingest still enqueues through RQ.
- The MusicBrainz mirror stack (its own change, ADR 0005).
- GPU worker deployment (needs GPU passthrough to docker-0 verified first).
- Cloudflare Tunnel and DNS configuration, which live in Cloudflare and stache-infra, not this repo.
- Backups: tracked as a task here, implemented with the rack-wide backup work in stache-infra.

### Current state (observed)

- CI builds four images and pushes none (`.github/workflows/ci.yml:42-58`), and runs only `pytest -m unit`.
- `compose.yml` runs Postgres 15, Redis, API, web, bot, worker and a GPU `extraction` profile.
- `.env.example` lists `SPOTIFY_REDIRECT_URI`, `SPOTIFY_RECS_ENABLED`, `LASTFM_SIMILAR_ENABLED`, `AUDIO_ROOT`, `CACHE_DIR`, `MUSICBRAINZ_RATE_LIMIT` and `POSTGRES_HOST`; none is read by code under `services/`, `apps/` or `packages/` (grep, 2026-10-25).
- `/health` returns HTTP 200 with `"status": "degraded"` when the DB is down (`services/api/main.py:78-91`).
- `deploy/Caddyfile` targets `sidetrack.network` with Caddy; Stache-Rack uses Traefik.
- Assumed (from stache-infra docs marked unverified): node labels `gpu=true` on docker-0; docker-1 has the most free disk (~83 GiB).

## Capabilities

### New Capabilities

- `platform/runtime-config`: how services obtain configuration and secrets at runtime.
- `platform/health`: what health endpoints report, for orchestrator healthchecks.

### Modified Capabilities

None.

## Impact

- `.github/workflows/ci.yml`, `compose.yml`, `deploy/`, `.env.example`, `config/ENVIRONMENT.md`
- `services/api/config.py`, `services/api/main.py`
- `apps/web/app/lib/config.ts`, `apps/web/Dockerfile` (build arg for the public API URL)
- GitHub repo settings and GHCR packages
- Stache-Rack: a new Portainer stack, Swarm secrets, a node label for the DB, and Cloudflare Tunnel hostnames (applied by the owner, documented in stache-infra)
