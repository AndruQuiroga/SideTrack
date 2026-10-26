# Tasks

## 1. Transactional queue foundation

- [x] 1.1 Pin Procrastinate and add the versioned queue schema plus application job/schedule mappings and Alembic migration; prove clean Postgres 16 installation, library schema objects, application metadata agreement and upgrade from the Phase 1 head in `services/api/tests/test_migrations.py` and `tests/test_queue_migrations.py`. Record the selected version/schema provenance and worker configuration in `docs/JOBS.md`.
- [x] 1.2 Implement the sync SQLAlchemy/psycopg transaction adapter and public job UUID mapping; prove separate-connection commit visibility, rollback atomicity and connection ownership in `tests/test_queue_transactions.py` before converting producers.
- [x] 1.3 Add worker composition and domain public task registration, default/musicbrainz versus gpu queue selection, global musicbrainz serialization and request pacing; prove multi-worker isolation, one-second request spacing, unavailable task handling and module boundaries in `tests/test_worker_queues.py` and `tests/test_import_boundaries.py`. Document queue selection in `docs/JOBS.md`.

## 2. Existing job APIs and reliable execution

- [x] 2.1 Move both API producers and polling to Postgres while preserving acceptance/response fields and returning sanitized 503/404/error codes; prove ingest and taste-profile enqueue/run/poll, persisted results after restart and error redaction in `services/api/tests/test_jobs.py`. Update `tests/test_job_compatibility.py` and the Phase 0 contract comparison to explicitly permit the planned additions while retaining all prior routes and schemas; document ID retention and status mapping in `docs/JOBS.md`.
- [x] 2.2 Implement persisted attempts, bounded retries, execution time bounds, graceful shutdown, stalled recovery and public/library status reconciliation; prove crash-before-commit, crash-after-domain-commit, crash-after-result-write, terminal failure and SIGTERM behavior using real worker subprocesses in `tests/test_worker_recovery.py`, including retry-safe taste recomputation. Document recovery and safe failure codes in `docs/JOBS.md`.
- [x] 2.3 Implement persisted recurring/one-shot schedule reconciliation, unique occurrences and cleanup retention; prove competing schedulers, coalesced missed recurrences, restart persistence and no replay after cleanup in `tests/test_job_schedules.py`. Document explicit schedule enablement and the absence of automatic Last.fm polling in `docs/JOBS.md`.

## 3. Listening checkpoints

- [x] 3.1 Add listening-owned per-account checkpoints with user cascade, seed from existing latest listens, and move import transaction ownership to the caller; prove restart resume, failed-import rollback, account isolation, explicit since_ts and monotonic updates in `tests/test_import_checkpoints.py`. Document the retained 200-record/no-backfill limit in `docs/JOBS.md`.
- [x] 3.2 Make overlapping/replayed imports conflict-safe under per-account locking and terminate deleted-user jobs safely; prove concurrent overlapping payloads, commit-before-ack replay, checkpoint cascade and no user resurrection in `tests/test_import_checkpoints.py` and retain `tests/test_ingest_boundary.py` coverage.

## 4. Durable club delivery

- [x] 4.1 Reconcile club-owned notification occurrences transactionally with week writes, invalidate superseded revisions, seed future deadlines and create unique outbox events; prove rollback, edits/removals/deletes, competing workers, catch-up and expired reminder suppression in `tests/test_club_schedules.py`. Document unchanged notification meaning and cutover seeding in `docs/JOBS.md`.
- [x] 4.2 Add authenticated notification claim/ack/fail APIs with database-time leases, token validation, retry backoff and visible terminal failures; prove unauthorized access, parallel claims, stale acknowledgment, lease recovery, revision invalidation and failed delivery limits in `services/api/tests/test_club_notifications.py`. Document the API and at-least-once guarantee in `docs/JOBS.md`.
- [x] 4.3 Update the generated API client and replace bot week timers/startup scheduling with outbox polling and Discord send/ack delivery; prove restart-before-send, ack-after-send, send-before-crash recovery, missing targets, retryable/permanent errors and cancellation on shutdown in `apps/bot/tests/notification-delivery.test.ts`, using test doubles only under tests. Verify `pnpm -r run lint`, `pnpm -r run test` and `pnpm -r run build`; document the send/ack duplicate window in `docs/JOBS.md`.

## 5. Runtime cutover and integration

- [x] 5.1 Remove Redis/RQ/APScheduler/unused Redis limiter dependencies, config and deployment services; retire dormant Spotify worker jobs and provide explicit legacy startup behavior while preserving unrelated aliases. Update Compose, Swarm, CI, Docker, examples, README, MODULES.md, deploy runbook, ADR 0002 and ADR 0006. Prove no supported runtime needs Redis, old worker startup reports retirement, and stack docs cover configuration in `tests/test_worker_startup.py`, `tests/test_runtime_dependencies.py`, `tests/test_module_layout.py` and `scripts/check_stack_docs.py`.
- [x] 5.2 Verify the integrated API/worker/bot against temporary migrated Postgres 16 without Redis, including drain/cutover/rollback rehearsal and restart recovery, in `tests/test_jobs_end_to_end.py`; build the API and bot images, run the full Python/TypeScript suites, Ruff, import-linter and strict OpenSpec validation. Preserve the visible mypy backlog and deferred real OAuth/rack checks.
- [x] 5.3 Update `docs/status.yaml` and regenerate `docs/STATUS.md`, recording only demonstrated capabilities and test evidence; update ROADMAP.md with actual Phase 2 progress. Prove generated status and evidence validity with `services/api/tests/test_gen_status.py` and `uv run --frozen --extra api python scripts/gen_status.py --check`.

## Workflow follow-up

CI repair (#288): reproduced the Linux `--once` SIGTERM failure from PR #287,
then moved signal handling to the outer worker lifetime. Both continuous and
drain-mode SIGTERM subprocess regressions pass. The complete Linux CI test
selection passes 132 tests, with only the opt-in image rehearsal skipped;
Ruff and all six import contracts pass. The test assertions remain strict.

Verification on 2026-10-25: 130 Python tests pass. The normal run skips the opt-in
image rehearsal and host-Windows SIGTERM test; the explicit API/worker/bot image
rehearsal passes Linux SIGTERM, API restart, bot send/ack, and rollback to the
saved Phase 1 API followed by restoration of Phase 2 with results intact.
All 19 web/bot tests, workspace lint/build, Ruff, six import contracts, migration
drift checks, deployment-document coverage and strict OpenSpec validation pass.
Mypy retains 39 existing errors and reports none in the new Phase 2 modules.
No real Discord messages were sent; real Last.fm OAuth and rack rollout remain
deferred. Issue #286 tracks the separately discovered ORM user-deletion defect.

- Review the Phase 1 and Phase 2 changes separately; do not merge automatically.
- Archive only when all tracked behavior has evidence for every spec scenario.
- Real Last.fm account verification and first rack deployment remain explicit operational follow-ups, not completed Phase 2 implementation claims.
