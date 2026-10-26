# Design

## Context

See proposal.md for motivation and the three delta specs for acceptance criteria.
Observed: API submission routes enqueue two serialized `services.api.jobs.*`
functions. `sidetrack/listening/ingest.py` commits its own session and derives its
starting timestamp from listens; overlapping inserts can violate the existing
dedup constraint. `Week` stores deadlines and Discord thread IDs but no phase
state. The bot currently schedules four notices with in-memory timers.

## Goals / Non-Goals

**Goals:** replace queue infrastructure while preserving domain ownership,
existing job response fields and notification meaning. Make retries, schedules,
checkpoints and delivery recoverable using the existing Postgres service.

**Non-Goals:** see proposal.md. This change adds no automatic Last.fm polling
default, new phase state machine or analysis implementation. Schedule primitives
support explicitly enabled recurring work; current club deadlines are one-shot.

## Decisions

### Queue library and transaction ownership

Choose Procrastinate, an option already permitted by ADR 0002, for its retries,
task locks and explicit external-connection deferral. PgQueuer was considered;
Procrastinate's documented transaction hook fits the existing sync SQLAlchemy /
psycopg 3 API. Pin a Python 3.11-compatible release exposing that hook using uv.
The API adapter passes the SQLAlchemy session's underlying psycopg connection
to SyncPsycopgConnector; it must not commit or close that borrowed connection.
Prove commit, rollback and visibility with separate real Postgres connections
before migrating callers. Workers use a separate PsycopgConnector lifecycle.

Sources: [external connections](https://procrastinate.readthedocs.io/en/stable/howto/production/external_connection.html),
[schema migration](https://procrastinate.readthedocs.io/en/stable/howto/production/migrations.html).
Upstream SQL migrations must be integrated explicitly; worker startup does not
silently create schema. Vendor the pinned release's initialization SQL with its
license and checksum under migrations, invoked through a new Alembic revision.
Place library objects in a dedicated `job_queue` schema. Keep application ORM
tables in the existing schema; drift checks continue covering every application
table and separately verify library schema/version and functions. Do not broadly
exclude tables merely to make autogenerate pass.

### Ownership and stable job API

Shared queue infrastructure owns application `background_jobs`, `job_schedules`
and occurrence records; listening owns `import_checkpoints`; club owns
`club_notification_outbox`. Add all application mappings to the canonical
registry. Domain task handlers live in domain modules with public operations;
worker composition registers them. Shared queue infrastructure does not import
domain internals. Extend import-boundary tests to cover this direction.

Use a public UUID string in `background_jobs`, linked to the library job ID.
Store task kind, safe result, safe error code and attempts. Keep existing API
response fields; map scheduled/retrying work to deferred, pending to queued,
running to started and terminal states to finished/failed/canceled. Persist
results before acknowledging success; terminal error synchronization and stalled
job recovery reconcile the application row with actual queue state. Test failure
between these steps. Unknown/malformed public job IDs return 404. Roll back
submission errors and return sanitized 503; never accept work on an unavailable
database. Results and errors use allowlisted fields, never raw exceptions.

The taste-profile handler keeps current behavior; retry safety must be proven
against its existing upsert path. Unavailable analysis remains unavailable.
Preserve legacy function import identity; replace tests that insist on RQ
serialization with public-job compatibility tests. Old RQ transport is drained
at cutover, not supported alongside the replacement.

### Execution and schedules

`python -m sidetrack.worker` is the supported entrypoint. Default CPU startup
consumes `default` and `musicbrainz`; an explicit `--queues gpu` mode is reserved
for the GPU node and does not register fabricated handlers. Refuse mixed GPU/CPU
queue configurations. Library locks serialize musicbrainz tasks across processes;
a Postgres-owned next-request timestamp enforces the web API's one-second gap
between requests, including multiple calls within a task. Existing inline catalog
lookups are not relocated into a new asynchronous resolution pipeline here.

Default retry budget is three total attempts with bounded exponential backoff;
permanent validation/unavailable errors terminate without retry. Apply equivalent
bounded recovery to stalled jobs using the library recovery mechanism, exercised
by killing a worker subprocess. Ingest and recompute retain their current ten-
and five-minute execution bounds. SIGTERM stops new claims and allows up to 30
seconds for completion before exit; stalled recovery handles interrupted work.
Sidetrack owns the outer signal context and disables the library's inner signal
context, which ends before draining in `--once` mode. Canceling the library's run
task requests its bounded graceful drain; intentional signal cancellation is
treated as a successful process shutdown. Regressions cover continuous and
`--once` workers as regular Linux subprocesses (issue #288).

A small reconciler in the worker uses row locks and unique
`(schedule_id, revision, due_at)` occurrences. It defers jobs and advances schedules
in one transaction. Multiple reconcilers are safe. Use database UTC time. For
recurrences, coalesce downtime into one catch-up occurrence and move next_due_at
forward. No external scheduler or independent stateful service is introduced.
Retain terminal public job results for 30 days and delivered outbox rows for
30 days; schedule cleanup through the same persisted mechanism. Retain schedule
occurrence identity until its schedule is retired so cleanup cannot replay it.

### Checkpoint safety

Key checkpoints by user, provider and account identity, with user-delete cascade.
Seed missing Last.fm checkpoints from the existing latest-listen timestamp for
compatibility. Acquire a transaction-level account lock to serialize competing
imports, read the checkpoint, fetch the same current 200-record payload, and use
conflict-safe listen insertion. Commit domain rows and monotonically advanced
checkpoint together. Refactor the existing ingest helper so its caller owns the
transaction; preserve the legacy public operation through a wrapper if needed.
Explicit since_ts affects fetch start only. No pagination or repair of dropped
album-less scrobbles is implied. Provider/account IDs are job arguments;
credentials remain runtime configuration. Deleted users yield a safe terminal
user-unavailable error without resurrecting data.

### Durable Discord delivery

Week create/update calls a club public operation that reconciles one-shot schedule
rows before the week transaction commits. Revision changes invalidate old
occurrences and unclaimed outbox rows. Due handlers check current revision and
thread IDs before inserting an event with a unique occurrence key. Preserve the
current four notice kinds and target fallback; no phase/winner mutation occurs.
Initial migration seeds only future deadlines for existing weeks. Thereafter,
restart catch-up delivers missed close/phase notices, but skips one-hour notices
after closing. Missing targets are skipped with a visible reason.

Add service-authenticated POST claim, acknowledge and fail operations under
`/club/notifications`. Claim batches use SKIP LOCKED, a 60-second lease and a
random token per event; acknowledgments condition on event ID/token/expiry.
Claim/ack/fail response payloads contain only delivery information, no credentials.
Use database time for leases. Permanent failures and three exhausted delivery
attempts become failed; transient failures use bounded backoff and Discord retry
timing. Expired claims are reclaimable. Revision checks prevent new claims for
obsolete pending notices; a message already in flight can still be sent.

The bot polls this API every five seconds, sends via its existing Discord client,
then acknowledges with the message ID. Its timer only wakes polling; deadlines
and retry state remain in Postgres. Remove startup week scheduling and the
`scheduleForWeek` calls from command handlers. Update the API client and test bot
restart/ack behavior with test doubles under tests. Delivery is at least once:
Discord acceptance followed by a crash before acknowledgment can duplicate a
message. Do not promise exactly-once external delivery.

### Infrastructure retirement

Remove Redis/RQ/APScheduler and the unused Redis limiter dependency from the
root extras and lockfile, config examples, Compose/Swarm, and supported runtime
imports. Keep the worker extra as the supported queue dependency group. Remove
dormant worker scheduling code and unsupported Spotify-only job paths; retain an
actionable `python -m services.worker` retirement error. Legacy RQ entrypoints
can forward to the new worker with an operator migration notice, without
importing RQ. Retain unrelated API/domain aliases. Update ADR 0002 with the
selected library and ADR 0006's worker command as implementation follow-through.

## Risks / Trade-offs

- At-least-once execution/delivery -> database deduplication, monotonic checkpoints,
  unique occurrence keys and documented Discord send/ack window.
- Library schema and application status can drift -> pinned schema, explicit
  migrations and crash-point reconciliation tests, no ad hoc startup DDL.
- Account lock spans external I/O -> bound request timeouts; only that account's
  imports serialize. This small personal workload favors correctness.
- Status results expire -> document 30-day retention and return 404 thereafter.
- Existing mypy backlog -> retain current reporting; do not weaken CI gates.

## Migration Plan

1. Verify Phase 1 checks. Run new migration and recovery tests on temporary
   Postgres 16 + pgvector, then build the shared API/worker image and bot.
2. Pause existing producers and bot reminders. Drain the old RQ worker; inventory
   queued/failed jobs without dumping credentials. Do not discard accepted work.
3. Apply Alembic while producers are paused. Start matching API/worker/bot images,
   with only CPU queues enabled. Seed future club deadlines once; remove Redis.
4. Verify a real local enqueue/run/poll cycle, restart recovery and reminder delivery
   using test destinations. First rack rollout and real OAuth remain separate
   operational checks in ROADMAP.md.
5. Before new producers resume, rollback may restore the old image/Redis stack,
   leaving additive Postgres tables unused. After accepting new Postgres jobs,
   pause producers and drain/reconcile them with the new worker before rollback;
   an old image cannot consume the new queue. Do not drop durable state as part
   of image rollback. No automatic merge or rack deployment.
   The old API must bypass its migration-running entrypoint with a direct uvicorn
   command after schema compatibility is verified: old Alembic code cannot
   resolve new revision IDs. Rehearse old user/week reads and restoration of
   the new API with its job results intact; restore old Redis before old producers.
