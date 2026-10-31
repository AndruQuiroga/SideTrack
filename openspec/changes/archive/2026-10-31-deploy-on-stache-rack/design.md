# Design

## Context

Stache-Rack conventions come from the stache-infra docs (`docs/architecture/service-exposure-models.md`, `persistent-storage-model.md`, `operations/secrets-and-credential-handling.md`, the runbook's "Standard deployment patterns", and `stacks/uptime-kuma/portainer-stack.yml` as a template). Many of their hardware claims are marked unverified, so placement here uses node labels the owner sets rather than hostnames. This change lands after `harden-api-credentials`, which introduces `SIDETRACK_ENV` and `SIDETRACK_LINK_SECRET`.

## Goals / Non-Goals

**Goals:**
- One `deploy/stack.yml` that Portainer can deploy unchanged, with secrets supplied outside the repo.
- CI that produces deployable, immutable image tags.

**Non-Goals:**
- Continuous deployment from CI into the rack. Portainer pulls a tag the owner chooses; CI never needs rack credentials.

## Decisions

**Images per service on GHCR, tagged by SHA.** `sidetrack-api`, `sidetrack-web`, `sidetrack-bot`, built with `docker/build-push-action` and the GitHub Actions cache. `main` also moves a floating `main` tag for convenience; the stack file references `${SIDETRACK_TAG}` so deploys pin a SHA. The worker image is dropped: the RQ consumer for Last.fm ingest runs from the API image with a different command (`python -m services.api.rq_worker`).

**Separate API hostname.** NextAuth owns `/api/auth/*`, so a path prefix would collide. The API gets `api.sidetrack.network` (public) and `api.sidetrack.stache.lan` (LAN). The browser bundle gets `NEXT_PUBLIC_API_BASE_URL=https://api.sidetrack.network` as a build arg. Server-side code in the web app prefers `SIDETRACK_API_BASE_URL=http://api:8000` (the stack's internal overlay), so `getApiBaseUrl()` branches on `typeof window`. CORS allows `https://sidetrack.network` and `http://sidetrack.stache.lan`.

**Placement by labels.** Postgres pins with `node.labels.sidetrack.db == true` and binds `/srv/sidetrack/postgres`. The owner labels one node (docker-1 has the most free disk per stache-infra). Stateless services carry `node.labels.arch == amd64` like the wedding stack. A label instead of a hostname keeps the stack file valid if the data moves.

**Secrets.** Swarm external secrets: `sidetrack_postgres_password`, `sidetrack_api_token`, `sidetrack_link_secret`, `sidetrack_discord_bot_token`, `sidetrack_discord_client_secret`, `sidetrack_nextauth_secret`, `sidetrack_lastfm_api_secret`, `sidetrack_spotify_client_secret`. The API uses pydantic-settings' `secrets_dir`. The Node services read `*_FILE` variables through a 10-line helper, since neither Next.js nor discord.js reads secret files natively. Non-secret config goes in Portainer stack env.

**Postgres 16 with pgvector.** Image `pgvector/pgvector:pg16`, matching the wedding stack's major version and ready for ADR 0004. Compose moves to the same image so local and rack match.

**Redis stays, ephemeral.** `redis:7-alpine` with `--save "" --appendonly no`, no volume, internal overlay only. It's removed in Phase 2 along with RQ.

**Health.** `/health` sets a 2-second statement timeout and returns 503 on failure. The stack healthchecks use it; Uptime Kuma gets `https://api.sidetrack.network/health` and `http://sidetrack.stache.lan`.

**Branch protection.** Require the `python`, `node` and `images` checks on `main`; no required reviews (single owner). Set via `gh api` after the workflow names are final.

## Risks / Trade-offs

- [The docker-1 disk and GPU claims are unverified] → Label-based placement; the owner verifies before labelling. The GPU worker is out of scope.
- [The baked public API URL ties web images to one domain] → Acceptable for a single deployment; the build arg makes another domain a rebuild, not a code change.
- [A public API exposes unauthenticated GETs until Phase 3] → Same exposure as today. Change 1 removes the credential leak. Cloudflare can restrict `api.` to the web origin later if needed.
- [Postgres 15 → 16 for existing local volumes] → Local data is disposable. No rack data exists yet.

## Migration Plan

1. Merge; CI pushes images tagged with the SHA.
2. Owner: create Swarm secrets, label the DB node, create `/srv/sidetrack/postgres`, add the Portainer stack from `deploy/stack.yml` with `SIDETRACK_TAG=<sha>`, add the Cloudflare Tunnel hostnames and AdGuard/Traefik LAN names, and record it all in stache-infra.
3. Rollback: redeploy the previous SHA tag in Portainer; Postgres data stays on its bind mount.

## Open Questions

- Backup method for `/srv/sidetrack/postgres` (nightly `pg_dump` to the HDD vs the rack-wide solution). This doesn't affect the stack shape and can be settled with the stache-infra backup work.
