# Status

Hand-maintained until `scripts/gen_status.py` exists (Phase 0). Last reviewed 2026-10-25 from code reading, not from running the system. If code and this file disagree, the code wins: fix this file.

Status values: **works** (implemented end to end), **partial** (implemented with known gaps), **broken** (implemented but cannot succeed), **stub** (placeholder, returns nothing useful), **absent**.

## Club (Discord album club)

| Capability | Status | Notes |
| --- | --- | --- |
| Create week, nominate, edit/withdraw nomination | works | API + bot |
| Ranked ballot (rank 1 and 2) | partial | No self-vote, phase or duplicate-pick checks (`routes/votes.py`) |
| Ratings and summary | works | |
| Reminders and phase transitions | partial | In-memory `setTimeout` in the bot; lost on restart; transitions only post messages |
| Album metadata from Spotify | works | Client credentials, metadata only (`external/spotify.py`) |
| Web archive (weeks, winners) | works | |

## Listening

| Capability | Status | Notes |
| --- | --- | --- |
| Last.fm account link | partial | Signed-state flow implemented and tested (`harden-api-credentials`); not yet verified end to end against real Last.fm |
| Last.fm scrobble import | partial | Newest 200 only, no backfill; scrobbles without an album are dropped |
| Spotify listen sync | broken | Inserts listens for tracks that don't exist (FK failure); no Spotify OAuth |
| ListenBrainz import | absent | |
| MusicBrainz resolution | partial | Per-scrobble web API calls inside the import job |

## Analysis

| Capability | Status | Notes |
| --- | --- | --- |
| Audio feature extraction | stub | `services/extraction` is an empty FastAPI app |
| Embedding models (any) | absent | Pre-reboot adapters (CLAP, OpenL3, PANNs, MusicNN) returned fake numbers and were deleted |
| Spotify audio features | broken | Endpoint returns 403 for apps created after 2024-11-27 |
| Taste profiles, compatibility, recommendations | stub | Tables exist; values derive from empty features |

## Platform

| Capability | Status | Notes |
| --- | --- | --- |
| Auth | partial | Writes need the service token and the API fails closed without it; stored credentials are never returned. No per-user auth yet (Phase 3); GETs are public |
| Web fallback data | broken | `apps/web/app/lib/api/{weeks,profile,feed}.ts` show sample weeks, profiles and feed items when the API fails, which violates the no-fakes rule |
| Background jobs | partial | Redis (ephemeral) + one RQ consumer for Last.fm ingest. The legacy `services/worker` (APScheduler, Spotify sync) is no longer built or run; Phase 2 replaces RQ |
| Health checks | works | `/health` returns 503 within 2 s when the DB is unreachable (verified live, 2026-10-25) |
| Runtime secrets | works | API reads `/run/secrets/<name>`; web and bot read `<NAME>_FILE` |
| Tests | partial | 57 API tests (SQLite, not Postgres yet); 6 web and 4 bot unit tests; no worker tests |
| Type checking | broken | 44 pre-existing mypy errors; CI runs mypy as non-blocking until fixed |
| CI | works | Lint, tests, OpenSpec validation and image builds pass on PRs; `main` pushes `ghcr.io/andruquiroga/sidetrack-{api,web,bot}` (first green run 2026-10-25, PR #280). Required for merging into `main` |
| Image visibility | works | GHCR packages are public, matching the public repo (owner's choice, 2026-10-25). Images contain no secrets; switch to private in package settings if needed |
| Deployment to Stache-Rack | partial | `deploy/stack.yml` and runbook ready; never deployed. Local compose verified healthy (db, redis, api, web, rq-worker) |
