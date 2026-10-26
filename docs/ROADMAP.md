# Refactor progress

This is a phase index, not a claim that planned capabilities work. See STATUS.md
for observed behavior and openspec/changes/ for implementation tracking.

## Phase 0: honest baseline and deployment preparation

PRs #280–#282 delivered OpenSpec, credential hardening, runtime secrets and health
checks, deployment artifacts, removal of invented page data, Postgres migration
tests, and a generated status report. The follow-up
`remove-fabricated-connection-status` removes an overlooked default linked account
and distinguishes unavailable account data from an empty successful lookup.

Two operational checks remain explicitly visible:

- `harden-api-credentials` task 3.4: the owner deferred the real Last.fm account
  test on 2026-10-25. Automated credential tests and the web build pass; linking
  stays **partial** until the real flow succeeds.
- `deploy-on-stache-rack`: first rack rollout and its infrastructure records are
  still pending. Preparation tasks being complete does not mean deployment works.

These checks remain open while Phase 1 code work proceeds, as authorized by the
owner on 2026-10-25. Neither change should be archived as fully verified yet.

## Phase 1: module boundaries

Implement ADR 0001: a canonical `sidetrack` Python package with `identity`,
`catalog`, `listening`, `club`, and `analysis` modules. Modules own their tables;
cross-module writes go through public functions. Enforce boundaries with
import-linter in CI and preserve existing API and database contracts.

The implementation is tracked by `modularize-python-package`; ownership details
are in MODULES.md. Checks compare the API with a Phase 0 snapshot, verify migrated
Postgres metadata, and reject illegal module imports.

Do not implement the later phases while moving code. Postgres-backed background
jobs are Phase 2 (ADR 0002); per-user API authorization is Phase 3. Audio analysis
starts with the separate benchmark described by ADR 0004.

Phase 1 implementation is complete (5/5 tracked tasks). Reverification on
2026-10-25 passed all 87 Python tests against migrated Postgres, 11 web tests,
4 bot tests, six import contracts, Python and TypeScript lint, TypeScript builds,
strict OpenSpec validation and the generated-status check. Existing mypy errors remain the
recorded backlog; the Phase 0 operational checks above remain deferred.

## Phase 2: durable background work

`replace-rq-with-postgres-jobs` implements ADR 0002: Procrastinate/Postgres jobs,
transactional submission, persisted schedules and Last.fm checkpoints, bounded
retry/recovery, isolated queue lanes, and leased Discord notification delivery.
Redis/RQ/APScheduler and the dormant Spotify worker are retired. Cutover and
rollback procedures are in JOBS.md and the deployment runbook.

Verification includes migrated Postgres 16, competing connections/workers,
process interruption, API contract preservation, bot send/ack tests, and local
API/worker/bot images without Redis. The image rehearsal checks persistence after
API restart and graceful Linux SIGTERM, using a test sender instead of Discord.
All 14 implementation tasks are complete. Verification passed 130 Python tests,
19 web/bot tests, workspace builds/lint, six module contracts, migration drift,
status generation and strict OpenSpec validation. The separate image rehearsal
also passed, including rollback to the saved Phase 1 API and return to Phase 2
with new job results retained. Its temporary containers/network were removed.

CI follow-up #288 fixes SIGTERM during `--once` drain by retaining the signal
handler through the full worker lifetime. The complete Linux CI test selection
now passes 132 tests, including shutdown in both continuous and drain modes.

The pre-existing user-deletion ORM cascade defect found during checkpoint testing
is tracked separately in GitHub issue #286. Mypy retains 39 existing errors; the
new modules add none. GPU analysis, import backfill and phase enforcement remain
later work. Real OAuth verification and first rack deployment remain deferred.

## Phase 3: per-user API authorization

ADR 0009 (proposed) decides the model: the web server holds user sessions; the API
trusts per-client tokens (web, bot) that name the acting user with
`X-Sidetrack-Act-As`. GETs stop being public; club data is visible to club members,
personal listening data to its owner unless they share it with the club, and ballots
to the voter only. `add-per-user-authorization` holds the proposal, four behavior
specs, design and tasks; it passes strict OpenSpec validation. Implementation has
not started and waits for Phase 2 to merge, because both edit the same routes, the
generated client and the Alembic chain; its migration is `0008_per_user_authorization`.
Encrypting stored provider tokens at rest is separate Phase 3 work.
