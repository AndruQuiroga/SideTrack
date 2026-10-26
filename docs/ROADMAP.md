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
now passes 133 tests, including shutdown in both continuous and drain modes,
and synchronized queue-isolation checks with one and two slots per worker.

The pre-existing user-deletion ORM cascade defect found during checkpoint testing
is tracked separately in GitHub issue #286. Mypy retains 39 existing errors; the
new modules add none. GPU analysis, import backfill and phase enforcement remain
later work. Real OAuth verification and first rack deployment remain deferred.

## Phase 3: per-user API authorization

ADR 0009 (accepted) sets the model. The web server holds user sessions, and the
API trusts per-client tokens (web, bot) that name the acting user with
`X-Sidetrack-Act-As`. GETs are no longer public. Club data is visible to club
members, personal listening data to its owner unless they share it with the club,
and ballots only to the voter.

`add-per-user-authorization` is implemented on `codex/phase-3-per-user-auth`
(19/19 tasks):

- Migration `0008_per_user_authorization` adds `club_members`,
  `users.listening_visibility` and job submitters.
- Every route declares a policy, listed in AUTHORIZATION.md, and routes without
  one are refused at startup.
- The bot acts for each interaction's Discord user and records membership as
  itself.
- The website calls the API only from server code, for the session user.

Verification on 2026-10-26: the Python suite on migrated Postgres, 15 HTTP checks
against a live API, and the TypeScript lint, build and test runs.

Still open:

- The owner hasn't merged or deployed the change.
- Real Discord sign-in hasn't been verified.
- Two crashes found on main are recorded in `docs/issues/metadata-alias-crashes.md`
  for a separate change.
- Encrypting stored provider tokens at rest is separate Phase 3 work.
