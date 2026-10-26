# Durable background work

The API, CPU worker and bot use Postgres for jobs, checkpoints, schedules and
notification delivery. Redis, RQ and APScheduler are retired (ADR 0002).

## Schema and startup

Procrastinate is pinned to 3.10.0 (Python 3.11). Its unmodified initialization SQL,
MIT license and SHA-256 are vendored in `migrations/vendor/procrastinate-3.10.0/`.
Alembic 0005 installs the library in `job_queue` and application queue tables in
public; 0006 adds listening checkpoints and 0007 adds the club outbox. Workers
never initialize schema. Application metadata drift and the library schema are
verified independently on Postgres 16 + pgvector.

Run migrations, then `python -m sidetrack.worker`. CPU workers consume `default`
and `musicbrainz` with concurrency four. `--queues gpu` selects a dedicated lane;
mixed GPU/CPU queues are rejected. Real GPU analysis remains unavailable.
`--once` drains runnable work and exits. The API image also runs the worker.
Legacy RQ entrypoints forward to it, while `python -m services.worker` exits with
retirement instructions and never schedules Spotify jobs.

Queue connections use `job_queue,public`. Submission borrows the SQLAlchemy
session's psycopg connection, temporarily applies that search path and restores
it. The adapter never opens a pool, commits or closes the caller's connection.
The producer owns commit; acceptance is returned only after it succeeds.

## Job API and execution

`POST /ingest/lastfm` and `POST /users/{id}/taste-profiles/recompute` retain their
202 fields, returning a public UUID string. Poll `GET /jobs/{id}/status` for
`job_id`, `status`, `result` and `error`. States remain queued, started, deferred,
finished, failed and canceled. Unknown IDs return 404; unavailable submission
returns sanitized 503. Results persist across API restarts. Errors are safe codes
such as unavailable, execution_failed, attempts_exhausted and worker_interrupted;
tracebacks and credentials are never response fields.

Domain work runs in child processes with a ten-minute Last.fm limit and a
five-minute limit for other tasks. A child watchdog also bounds orphan execution.
Windows uses the selector event loop required by psycopg; subprocess waits run
outside it. Credentials are runtime settings, never command-line arguments.
Graceful shutdown stops claims and allows 30 seconds for current work; the stack
allows 40 seconds. Sidetrack owns the signal context through the complete worker
lifetime, including the final drain in `--once` mode; the shorter library signal
context is disabled. Linux subprocess regressions cover both continuous and
drain modes (CI repair, issue #288). Interrupted/transient work retries with bounded exponential
backoff and at most three total attempts. Permanent validation or unavailable
operations stop immediately. A one-second maintenance loop recovers jobs whose
worker heartbeat is missing or over 30 seconds old. Committed domain/result
transactions reconcile without re-executing effects after a lost acknowledgment.

MusicBrainz jobs share a global execution lock. Every MusicBrainz HTTP attempt,
including transport retries and inline catalog calls, also holds a Postgres
request-pacing lock and leaves a 1.05-second gap after completion. A failed call
still commits its pacing reservation. This favors correctness over throughput.

Terminal job results and delivered notifications are retained for 30 days. The
persisted daily cleanup schedule keeps active acknowledgment windows and schedule
occurrence identities. Operators can inspect failed jobs/outbox rows in Postgres;
there is no new public scheduling or retry administration API.

## Listening checkpoints

Checkpoints are listening-owned and keyed by user, provider and normalized account.
Missing checkpoints seed from the existing latest-listen timestamp. An account
transaction lock serializes overlapping imports; duplicate listens are skipped
using the existing user/track/played_at constraint. Catalog writes, listens,
checkpoint advancement and the job result commit together. Explicit since_ts
changes the fetch start but never moves a saved checkpoint backward. Import still
reads the newest 200 records, has no backfill and can drop unresolved/album-less
records. No automatic Last.fm polling is enabled by default.

User deletion cascades checkpoints in Postgres; queued imports cannot recreate
deleted data. The pre-existing ORM user-deletion defect with dependent listens is
tracked separately in GitHub issue #286; it is not fixed by this queue change.
Real Last.fm account verification remains deferred.

## Schedules and Discord delivery

Enabled schedules, next deadlines and occurrence identity live in Postgres.
Competing reconcilers create one occurrence per revision/deadline. Missed recurring
work coalesces into one catch-up occurrence. Saving a week reconciles four one-shot
notification kinds in the same transaction. Deadline edits invalidate obsolete
pending notices. Initial cutover seeds only future deadlines; subsequent restarts
catch up saved close/phase notices and skip one-hour reminders after closing.
Missing targets are recorded as skipped, not sent. Notifications retain current
wording/target fallback; they do not enforce phases or select winners.

The bot polls every five seconds. Service-authenticated POST operations under
`/club/notifications` claim one event with a 60-second lease, acknowledge it with
the matching token and Discord message ID, or report a permanent/transient failure.
Expired claims are reclaimable; stale tokens return 409. Transient delivery uses
bounded backoff and Discord retry timing, up to three attempts; permanent or
exhausted errors remain visibly failed. The bot stops new delivery during shutdown.

Delivery is **at least once**. Discord can accept a message immediately before a
bot crash or acknowledgment outage, so a reclaimed event can send a duplicate.
No exactly-once external-delivery guarantee is made. Tests use send doubles under
tests; no verification sends real Discord messages.

## Cutover and rollback

Pause API producers and the bot, drain accepted RQ jobs with the old image, and
inventory any failures without dumping credentials. Stop the old worker. Apply
Alembic, then start matching API/worker/bot images and remove Redis. Only CPU queues
are enabled in the deployment. Do not discard accepted work.

Before new acceptance resumes, rollback can restore the previous images/Redis
stack while leaving additive Postgres tables unused. After new jobs are accepted,
pause producers and drain/reconcile them using the new worker before restoring an
old image: RQ cannot consume Postgres jobs. Never drop durable state during image
rollback. First rack rollout remains an operational follow-up, not a claim here.

An older image's automatic Alembic startup cannot resolve newer migration IDs.
After checking compatibility and draining new work, temporarily override its API
command with `uvicorn sidetrack.api.main:create_app --factory --host 0.0.0.0 --port 8000`
to serve against the retained additive schema. Restore the previous Redis stack
before resuming old job producers. Old images cannot serve new Postgres job IDs;
those results remain stored for the new API. The image rehearsal verifies old
user/week reads and restoration of the new API without deleting durable state.

## Verification

Run the normal Python suite plus `lint-imports`, and the workspace TypeScript tests,
lint and build. Queue tests use independent real Postgres connections, competing
workers, process termination and migrated metadata; external provider/Discord
responses are doubled only in tests.

For a local image rehearsal, build tags `sidetrack-api:phase2-check` and
`sidetrack-bot:phase2-check`, set `SIDETRACK_TEST_API_IMAGE` and
`SIDETRACK_TEST_BOT_IMAGE` accordingly, and set `SIDETRACK_TEST_PREVIOUS_API_IMAGE`
to a saved Phase 1 image (locally, `sidetrack/api:phase1-check`). Then run
`uv run --frozen --extra api --extra worker --extra dev pytest tests/test_jobs_end_to_end.py`.
It runs temporary containers without Redis, exercises real HTTP and bot delivery
code with a test sender, restarts the API, and checks Linux SIGTERM completion.
It also drains new work, serves reads through the previous image using the
rollback command, and returns to the new image with job results intact.
Its containers/network and the test database are removed afterward.
