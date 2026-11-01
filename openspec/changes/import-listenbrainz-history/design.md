# Design

## Context

See proposal.md (Why, Impact). What shapes the approach:

- **Existing import pattern.** `ingest_lastfm` (`sidetrack/listening/ingest.py`) takes a
  per-account advisory lock, reads or creates an `ImportCheckpoint`, resolves each track
  through `catalog.resolve_listen_track`, inserts with `ON CONFLICT DO NOTHING` on
  `uq_listen_event_dedup`, and advances the checkpoint in the job's transaction. The job
  runner (`sidetrack/job_runner.py`) runs each job in a child process with a 600 s limit for
  Last.fm.
- **Resolution drops plays.** `resolve_listen_track` needs an album to create a track and
  calls `resolve_recording_mbid` (MusicBrainz web API, 1 request/s) when no MBID is given.
  Most of the owner's listens are YouTube uploads with no release and often no mapping.
- **The export reader already exists**, but in the benchmark project (`audio_lab/seeds.py`),
  which never reads the database. Its rules (mapping first, "Artist - Title" split, upload
  noise, 30-minute sessions, night rule) are the ones the owner used to build and judge the
  benchmark seeds, so production should reproduce them, not reinvent them.
- **Data shape.** ListenBrainz's export `listens/*.jsonl` records and its API's `payload.listens`
  items share one shape: `listened_at`, `track_metadata.{artist_name, track_name,
  release_name, additional_info, mbid_mapping}`. The API is public for public users and
  paginates with `count` (max 1,000), `max_ts` and `min_ts`, with `X-RateLimit-*` headers.
  Task 1.1 confirms this before implementation.
- **Observed on the live API, 2026-10-31 (task 1.1).** `count=1000` returns 1,000 listens,
  and a larger `count` is accepted. Both bounds are exclusive. With only `max_ts` a page holds
  the listens just before it; with only `min_ts`, the listens just after it, still newest
  first. Every response carries `X-RateLimit-Limit` (30), `-Remaining`, `-Reset` and
  `-Reset-In`. `mbid_mapping` sits in `track_metadata` with `recording_mbid`, `recording_name`
  and `artists`, on 74% of the owner's listens, but holds no release name: only 31% have
  `release_name`. YouTube origins are `additional_info.origin_url` on `music.youtube.com`,
  `www.youtube.com` or `youtu.be`. The listen count endpoint said 74,919, and paging fetched
  74,928. `tests/fixtures/listenbrainz/page.json` is a synthetic page in this shape.
- **Corrections from that check.** 309 seconds hold more than one listen, so a page boundary
  can split a second (Decision 2). ListenBrainz moved 7 of 3,084 listens to another recording
  between one export and the API, so the track can't identify a listen (Decision 5). The
  export zip for 2026-10 held only 3,084 listens, so the API is the complete source.
- **Scale.** About 75,000 listens and (assumed) 10,000–15,000 distinct tracks for the owner.
  A club member who opts in later brings a similar order of magnitude.

## Goals / Non-Goals

**Goals:**
- Load the owner's full history in one sitting, restartably, without a MusicBrainz request.
- Keep one normaliser for the export and the API so the two paths can't disagree.
- Give downstream analysis a clean "chosen play" signal (sessions and night flags) and a
  local clock (timezone).

**Non-Goals:**
- Resolving unmapped listens to MusicBrainz recordings (ADR 0005 mirror work).
- Deciding what counts as music. Podcast and long-listen exclusion belongs to the profile
  change, which can version its rules independently of the import.
- Replacing the Last.fm import; both providers coexist, sharing the checkpoint table.

## Decisions

### Decision 1: One normaliser, two readers

`sidetrack/listening/listenbrainz.py` holds `normalise(record) -> NormalisedListen | None`
(artist, title, release, recording MBID, MSID, origin URL and YouTube ID, duration,
service, original artist and title). The export reader yields records from `listens/*.jsonl`;
the API client yields records from `payload.listens`. Both feed `store_listens(db, user,
records)`, which does resolution, insertion and counting. The rules are ported from
`audio_lab/seeds.py` (`resolve`, `clean_title`, `_video_id`), and a test fixture of a dozen
records with known answers pins them. audio-lab stays unchanged and separate (docs/MODULES.md).

One rule differs from `seeds.py`, which splits every unmapped "A - B" title. That would turn
`Some Song - Slowed` into an artist called `Some Song`. Production splits only when
the listen's origin is YouTube, which is what marks an upload channel in this history (5,997
of the 6,136 unmapped "A - B" titles).

Alternative: import audio-lab's functions. Rejected: audio-lab has its own environment and
is a benchmark tool; production can't depend on it.

### Decision 2: API backfill as a chain of page jobs

`listening.ingest_listenbrainz` arguments: `{user_id, mode: backfill|sync, max_ts?, until_ts?}`.
- **Backfill:** one job fetches one page (`count=1000`, `max_ts`), stores it, and queues the
  next job, until a page is empty or the oldest listen is older than `until_ts`. A full page
  stores all but its oldest second and passes `max_ts` = that second + 1, because `max_ts` is
  exclusive and a second can straddle the boundary; a short page stores everything. Each job commits its own page, so an interrupted
  chain leaves consistent data, and re-running the command restarts from the newest listen
  and skips duplicates (about 75 cheap requests for the owner's history). The result of
  each job records `next_job_id`, so the operator can follow the chain through
  `GET /jobs/{id}/status`.
- **Sync:** one job pages forward with `min_ts` = checkpoint, holding back a full page's
  newest second in the same way, until a page is short. A listen submitted late with a time
  older than the checkpoint is missed; a repeated backfill picks it up. With no checkpoint, a
  sync starts a backfill. A chain shares one run, so its last job's result holds the totals.
- **Time limit:** 600 s per job, the same as Last.fm; a page of 1,000 listens is DB work
  only and should take seconds, so this is generous.
- **Lock:** the same per-account advisory lock as Last.fm, keyed `listenbrainz:{user}:{account}`.

Alternative: one job that loops all pages. Rejected: a 75-page loop holds a transaction and
the job lock for minutes, and a failure late in the loop loses the whole run under the
current all-or-nothing job transaction.

### Decision 3: Checkpoint semantics stay "newest stored"

`import_checkpoints` is unchanged in shape; `provider` gains the value `listenbrainz`. The
checkpoint is the newest `listened_at` stored for the account. A backward backfill raises it
only on its first page (the newest), and later pages never lower it (spec: Backfill after
sync). Backfill progress is not persisted: it lives in the job chain's arguments, and the
restart cost is bounded by duplicates being cheap.

Alternative: add `oldest_ts` to the checkpoint row for resumable backfills. Rejected for
now: a column for a one-off process; re-running costs under a hundred requests.

### Decision 4: Tracks without an album, found by identity

Migration 0013 makes `tracks.album_id` nullable. Catalog gains a public operation
`resolve_track_identity(db, *, artist, title, release=None, recording_mbid=None)`:
1. by `recording_mbid` when given;
2. else by case-folded artist and title, and release when given (an expression index on
   `lower(artist_name), lower(title)` keeps this a lookup);
3. else create the track, with an album only when a release name is given (found by
   case-folded title and artist, or created bare), and `album_id = NULL` otherwise.

It never calls MusicBrainz. `upsert_album_from_release_group` can't be used, because it
searches MusicBrainz even for an album that already exists. `resolve_listen_track` is left as it is for Last.fm, so that
import's behaviour doesn't change in this change. Code that reads `track.album` already
tolerates `None` in `sidetrack/api/routes/search.py`; the web's listening pages render the
album as unavailable when absent, which `web/data-honesty` already requires for missing data.

Alternative: a synthetic "unknown release" album per artist. Rejected: it's a placeholder
that would show up as a real album in search and archives.

### Decision 5: Listen metadata is a curated subset

`listen_events.metadata = {"listenbrainz": {...}}` holds the normalised identifiers and the
original artist and title, not the whole payload. `listen_events` measured 62 MB with the
owner's 74,907 rows in the rehearsal, inside ADR 0005's budget. The MSID is kept because it is ListenBrainz's
stable key for a listen and lets a later change fetch feedback or mappings for it.

`uq_listen_event_dedup` keys on the track, which a remapped listen changes, so `store_listens`
also treats a stored listen with the same time and MSID as a duplicate.

### Decision 6: Sessions are a listening-owned table, rebuilt from the first new listen

`listen_sessions(id, user_id, started_at, ended_at, listen_count, kind, rule_version,
computed_at)` with `kind` in `unclassified | night_autoplay | unknown`, and
`listen_events.session_id` (nullable, `ON DELETE SET NULL`). `sessionize(db, user_id,
since=None, until=None)` deletes sessions within 30 minutes of that range and rebuilds them
from the listens, keeping a backward backfill's pages from rebuilding everything newer, so an import that stored listens touching the last
session extends it rather than creating a second one (spec: New listens extend the last
session). Each import job calls it for the time range it stored. The night rule is the
benchmark's: start hour 22–03 local, duration ≥ 3,600 s, count ≥ 12; `rule_version = "night-v1"`.

Alternative: compute sessions on read. Rejected: three downstream changes need the same
boundaries and flags, and the weekly profile has to cite the rule version it used.

### Decision 7: Timezone on the user

`users.timezone` (`String(64)`, nullable), validated against `zoneinfo.available_timezones()`
in the `PATCH /users/{id}` schema; the route already carries the self-or-admin policy
(docs/AUTHORIZATION.md). The import and sessionise operations read it; a missing zone
yields `unknown` session kinds and a `timezone_missing` note, never a guessed zone.

Alternative: a timezone argument on the import command. Rejected: three later changes
(profiles, clock, weekly card) need the same value, and it belongs to the user.

### Decision 8: Operator entry point

`python -m sidetrack.listening` (a `__main__.py` in the package) with subcommands
`backfill --user <id> [--until YYYY-MM-DD]`, `sync --user <id>`, `import-export --user <id>
--export <dir>`, `sessionize --user <id> [--rebuild]` and `schedule --user <id> [--enable]`.
The command lives in `sidetrack/listening_cli.py`, because it needs `sidetrack.models`, which
domain packages can't import; `__main__.py` only calls it. `backfill` and `sync` queue jobs
on the `default` queue and print the job IDs; `import-export` runs in-process on the
operator's machine (the export is on their disk), committing per file; `sessionize` runs
in-process. An optional persisted schedule, `listening.ingest_listenbrainz` in sync mode
every hour per linked account, is defined but disabled until the operator enables it.

### Decision 9: Autoplay flags are reviewable heuristics

The earlier draft named the non-flagged kind `active`. That implied deliberate listening,
which the rule cannot establish, so the kind is now `unclassified`. Overrides live in
`listen_session_overrides(user_id, started_at, ended_at, override in keep|autoplay,
set_at)`, keyed by session boundaries rather than session ID, so they survive rebuilds
while the boundaries are unchanged. `sessionize` re-applies matching overrides and reports
unmatched ones as `override_orphaned`. Routes: `GET /users/{id}/listening/sessions` and
`PUT|DELETE /users/{id}/listening/sessions/{session_id}/override`, self-only.
Downstream changes read `effective_kind`. See research notes §4 ("Self-report and
autoplay cautions") and §6.1.

### Decision 10: Provenance, UTC and import coverage

`listen_events.import_run_id` references a new `listening_import_runs(id, user_id,
provider, account, path in api|export, started_at, finished_at, outcome, counts json)`.
`played_at` stays `timestamptz`, stored in UTC; nothing converts to local time at import.
`import_coverage(user_id, provider, account, earliest_played_at, latest_played_at)` is
advanced in the same transaction as committed listens. Coverage is contiguous by
construction, because backfill pages walk backwards without gaps and sync walks forwards
from the checkpoint. The exception is a backfill interrupted after an older export: until it
finishes, coverage spans the gap between them. A retry is a new run; duplicates are counted, not stored.

## Risks / Trade-offs

- [ListenBrainz API shape or limits differ from the assumption] → Task 1.1 checks the live
  API first; the normaliser is pinned by fixtures, so a shape change fails tests, not data.
- [Catalog grows by about 15,000 album-less tracks] → They are real tracks the user played;
  search already handles missing albums. The expression index keeps resolution a lookup.
- [Night rule misfires on genuine late listening] → It is the rule the owner validated on
  the   benchmark seeds (36 sleep seeds, purity 0.63), and the flag is advisory. Users can review
  and override it (Decision 9), profiles disclose how many plays they excluded, and the rule
  is versioned.
- [A sync and a backfill job overlap for one account] → The advisory lock serialises them;
  duplicates are skipped either way.
- [Nullable album breaks a reader] → `grep` for `.album.` shows one reader, already
  null-safe; the web tests under `apps/web/tests` cover the listening pages, and task 3.3
  adds an album-less track to their fixtures.

## Migration Plan

1. Apply migration 0013 (nullable `tracks.album_id`, expression index, `users.timezone`, the
   session, run and coverage tables, and `listen_events.session_id` and `import_run_id`).
   Additive. Downgrading needs album-less tracks and their listens deleted first.
2. Deploy API and worker together (they share the image).
3. Set the owner's timezone, link the ListenBrainz account, run `import-export` from the
   owner's disk or `backfill` on the rack, then `sessionize`.
4. **Rollback:** disable the schedule, downgrade 0013. Imported ListenBrainz listens can be
   deleted by `source = 'listenbrainz'` if needed; Last.fm rows are untouched.

## Open Questions

- Whether to store `feedback.jsonl` loved tracks later (as a listening-owned table or a flag).
  No downstream change needs them yet; this is noted in proposal.md as out of scope.
