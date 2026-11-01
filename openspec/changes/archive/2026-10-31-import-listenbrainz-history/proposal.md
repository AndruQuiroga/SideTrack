# Proposal

## Why

Every feature in `docs/PRODUCT-VISION.md` (weekly mood and themes, the baseline of "normal
you", comfort against exploring, the listening clock, compatibility) reads the owner's
listening history, and that history is a ListenBrainz export on the owner's disk: 74,826
listens from 2019 to 2026 that Sidetrack's database has never seen. Until the history is in
Postgres, with its sessions and sleep-tab autoplay flagged for review, nothing
downstream can be built honestly.

## What Changes

- **ListenBrainz import.** A `listening.ingest_listenbrainz` job and an operator command
  import a user's listens from ListenBrainz: a full backfill through the public API (paged
  backwards in time) and incremental sync from a per-account checkpoint, in the same
  transactional, duplicate-safe way the Last.fm import works. The same normaliser also reads
  a ListenBrainz export directory (`listens/*.jsonl`) for an offline bulk load.
- **Honest resolution of upload-style listens.** Listens carry ListenBrainz's own
  `mbid_mapping` when it exists, and titles of the form "Artist - Title" from YouTube
  uploads are split as the benchmark seeds already do. Import never calls the MusicBrainz web
  API per listen. A listen whose release is unknown is still stored: the catalog gains
  tracks without an album rather than dropping the play.
- **Sessions and autoplay.** Listens are grouped into sessions, with a gap of 30 minutes
  starting a new one. A session that starts late at night, runs for an hour or more and
  holds 12 or more listens is flagged `night_autoplay`; everything else is `unclassified`.
  The flag is a heuristic, not evidence of sleep or intent. The user can review any
  session and set or clear a `keep`/`autoplay` override. Later changes read the
  *effective* classification and disclose what they exclude (research notes §4 and §6.1).
- **Provenance and coverage.** Each listen records its import run and path (API or
  export), with times stored in UTC. Each account records the earliest and latest
  imported time, so downstream features can tell "not imported" from "no listening".
  Retrying a failed import is safe.
- **A timezone per user.** Night detection, weekly boundaries and the listening clock need
  the user's local time. Users get an IANA `timezone` that the owner sets through the
  existing user update route; without it, sessions are still built but no night flag is set
  and the result says why.
- **Loved tracks** from the export's `feedback.jsonl` are **out of scope**; nothing downstream
  needs them yet.

Out of scope:
- Bulk MusicBrainz resolution of unmapped listens (ADR 0005's mirror). Unmapped listens keep
  the artist and title ListenBrainz gave.
- Classifying podcasts, too-long listens and YouTube pseudo-artists. The import stores what
  was played; the weekly profile change decides what counts for mood.
- Linking listens to audio assets (the separate `resolve-listens-to-audio` change).
- Any web page or bot command. The existing `GET /listen-events/` and
  `GET /users/{id}/listening/recent` routes return the imported rows unchanged.
- Last.fm backfill beyond the newest 200 (unchanged).

## Capabilities

### New Capabilities
- `listening/listenbrainz-import`: importing a user's ListenBrainz listens (API backfill,
  incremental sync, export files), how listens are normalised and resolved, and what the
  import reports.
- `listening/listen-sessions`: grouping listens into sessions, flagging likely night
  autoplay by a versioned heuristic, and letting users review and reverse the flag.
- `identity/user-preferences`: per-user preferences that other domains read, starting with
  the IANA timezone.

### Modified Capabilities
- `listening/import-checkpoints`: checkpoints are per user, provider and account, and the
  provider may be `listenbrainz` as well as `lastfm`. Transactional advancement, replay
  safety and deletion behaviour apply to both.

## Impact

Current state:
- **Observed:** `sidetrack/listening/ingest.py` imports only Last.fm (`ingest_lastfm`, newest
  200 tracks, checkpointed), and `sidetrack/job_runner.py` dispatches only
  `listening.ingest_lastfm`. `ListenSource.LISTENBRAINZ` and the `listenbrainz` provider
  already exist as enum values (`sidetrack/types.py`).
- **Observed:** `catalog.resolve_listen_track` (`sidetrack/catalog/metadata.py:306`) returns
  `None` without an album, so `ingest_lastfm` drops the listen, and it calls
  `resolve_recording_mbid` (a MusicBrainz web request) for every listen without an MBID.
  `tracks.album_id` is `NOT NULL` (`sidetrack/catalog/models.py`).
- **Observed:** `services/audio-lab/src/audio_lab/seeds.py` already parses the export
  (`listens/*.jsonl`), resolves `mbid_mapping` and "Artist - Title" uploads, cleans upload
  noise from titles, groups sessions at a 30-minute gap and flags night sessions. It is a
  benchmark tool that never reads the database (docs/MODULES.md), so production needs its own
  copy of those rules.
- **Observed:** `users` has no timezone (`sidetrack/identity/models.py`). `PATCH /users/{id}`
  exists.
- **Observed:** docs/STATUS.md lists "ListenBrainz import" as **absent**.
- **Assumed:** ListenBrainz's public listens endpoint returns listens for a public user
  without a token, at most 1,000 per request, with `mbid_mapping` and `additional_info`
  (including `origin_url`) in `track_metadata`. Task 1.1 confirms this against the live API
  before any code depends on it.

Affected:
- `sidetrack/listening/` (new importer, session model and operation, command entry point),
  `sidetrack/external/` (ListenBrainz client), `sidetrack/job_runner.py`,
  `sidetrack/worker.py` (time limit).
- `sidetrack/catalog/` (`tracks.album_id` nullable, `resolve_listen_track` extended),
  `sidetrack/identity/` (`users.timezone`), `migrations/` (0013).
- Docs: `docs/JOBS.md`, `docs/MODULES.md` (new listening table), `docs/status.yaml`, and a
  new `docs/LISTENING.md` for the operator commands.
- Scale: about 75,000 listens for the owner today; the design keeps the backfill to under
  100 API requests and one catalog resolution per distinct track.
