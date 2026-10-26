# Proposal

## Why

Observed: `sidetrack/queue.py`, `sidetrack/rq_worker.py` and the job-status route
depend on ephemeral Redis/RQ; `apps/bot/src/scheduler.ts` keeps reminder deadlines
in process memory. ADR 0002 requires durable background work in Postgres after
the Phase 1 module split.

## What Changes

- Use Procrastinate for Python jobs, with transactional submission, bounded
  retries, stalled-job recovery and persisted job results.
- Preserve the two existing job submission APIs and their polling response shape.
- Persist Last.fm import checkpoints and make retries safe against duplicate listens.
- Store schedules in Postgres and replace the bot's deadline timers with durable
  club notification events and a leased delivery outbox.
- Define `default`, serialized/rate-limited `musicbrainz`, and opt-in `gpu` queues.
  GPU processing remains unavailable until a real analysis implementation exists.
- **BREAKING operational change:** remove Redis, RQ and APScheduler dependencies,
  config and deployment services; retire the dormant `services/worker` runtime.
  Cutover drains existing RQ jobs; it does not deserialize Redis jobs into Postgres.

Out of scope: per-user authorization, Last.fm pagination/backfill, ListenBrainz,
Spotify listen sync/audio features, real GPU models, MusicBrainz mirror setup,
new voting/phase enforcement or winner selection, live OAuth verification and
first rack deployment. Preserve the current notification wording/meaning;
notifications must not be presented as proof of enforced club phase transitions.

## Capabilities

### New Capabilities

- `platform/background-jobs`: durable submission, execution, polling, queue
  isolation, retries, scheduling and retirement of the old queue runtime.
- `listening/import-checkpoints`: transactional Last.fm checkpoints and replay safety.
- `club/durable-notifications`: persisted week deadlines and restart-safe bot delivery.

### Modified Capabilities

None. Existing migration and status-report requirements continue to apply.

## Impact

Canonical queue infrastructure, domain public job operations, API job routes,
Alembic, Python dependencies/lockfile, bot scheduler and generated API client,
Compose/Swarm/CI, compatibility tests and deployment documentation. Observed:
`services/worker/__main__.py` still imports APScheduler and unsupported Spotify
jobs, although deployment does not run it. Replace that entrypoint with an
explicit retirement error; retain Phase 1 API/domain compatibility imports.
