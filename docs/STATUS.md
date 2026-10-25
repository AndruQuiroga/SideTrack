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
| Last.fm account link | broken | Connect endpoint never returns its URL; callback links any user via query param |
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
| Auth | broken | One shared bearer token for all writes; GETs unauthenticated; linked-account tokens readable |
| Background jobs | partial | Redis + RQ (two consumers) + APScheduler; cursors in memory |
| Tests | partial | 14 club API tests on SQLite; none for worker, bot, web |
| Deployment to Stache-Rack | absent | Compose file only |
