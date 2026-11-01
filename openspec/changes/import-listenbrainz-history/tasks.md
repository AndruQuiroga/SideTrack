# Tasks

## 1. Confirm the source

- [x] 1.1 Call the live ListenBrainz listens API for the owner's public account with `count=1000` and `max_ts`, and record in design.md Context the observed page size limit, the `mbid_mapping` and `additional_info.origin_url` fields and the `X-RateLimit-*` headers; verify by saving one sanitised page (no personal listens) as `tests/fixtures/listenbrainz/page.json` and noting the date in design.md

## 2. Schema and catalog

- [x] 2.1 Add migration 0013: `tracks.album_id` nullable with an expression index on `lower(artist_name), lower(title)`, `users.timezone`, `listen_sessions`, and `listen_events.session_id` (`ON DELETE SET NULL`); verify `services/api/tests/test_migrations.py` passes with no model drift
- [x] 2.2 Add `catalog.resolve_track_identity` (MBID, then case-folded artist/title/release, then create without MusicBrainz; album only when a release is given) and export it from the public catalog package; verify `tests/test_track_identity.py` covers the mapped, unresolved-with-release, unresolved-without-release, same-track-twice and no-MusicBrainz-request scenarios on Postgres
- [x] 2.3 Register `listen_sessions` as listening-owned in docs/MODULES.md and the ownership test, and keep `tracks` catalog-owned; verify `tests/test_module_layout.py` and `uv run --frozen --extra api --extra dev lint-imports` pass

## 3. Timezone preference

- [x] 3.1 Add `timezone` to the user model, `UserUpdate`/`UserRead` schemas and `PATCH /users/{id}` with IANA validation; verify `services/api/tests/test_user_preferences.py` covers the valid set, invalid zone (422), null read and the non-admin 403 scenarios
- [x] 3.2 Document the preference in docs/AUTHORIZATION.md's route table note for `PATCH /users/{id}` if its policy text changes, and in the new docs/LISTENING.md; verify the documented `PATCH` body is accepted by the API test

## 4. Normaliser and readers

- [x] 4.1 Add `sidetrack/listening/listenbrainz.py` with `normalise()` ported from `audio_lab/seeds.py` (mapping first, "Artist - Title" split for channel uploads, upload-noise cleaning, YouTube ID from `origin_url`) and a fixture of at least 12 records with expected results; verify `tests/test_listenbrainz_normalise.py` passes, including the mapped and channel-upload scenarios
- [x] 4.2 Add the ListenBrainz client in `sidetrack/external/listenbrainz.py` (public listens, `count`, `max_ts`, `min_ts`, rate-limit header handling that sleeps until reset); verify `tests/test_listenbrainz_client.py` with a stubbed HTTP transport covers paging and the rate-limit scenario
- [x] 4.3 Add `store_listens()` (per-account advisory lock, user-unavailable outcome, `ON CONFLICT DO NOTHING`, curated metadata, exact counts with `skipped` reasons and without-release count, time range); verify `tests/test_listenbrainz_store.py` on Postgres covers stored, duplicate, skipped, Last.fm-overlap and user-deleted scenarios
- [x] 4.4 Add the export reader for `listens/*.jsonl`; verify `tests/test_listenbrainz_export.py` shows export and API records for the same listen produce one identical row whichever runs first, and that the export path never appears in the result
- [x] 4.5 Add `listening_import_runs`, `listen_events.import_run_id` and `import_coverage`, advanced transactionally; verify `tests/test_listenbrainz_store.py` covers the provenance, before-the-first-import, covered-quiet-week and retry-after-failure scenarios

## 5. Jobs and checkpoints

- [x] 5.1 Add `listening.ingest_listenbrainz` (backfill page chain with `next_job_id`, sync from checkpoint) to `sidetrack/job_runner.py` and a 600 s limit in `sidetrack/worker.py`; verify `tests/test_listenbrainz_jobs.py` on Postgres covers the 2,500-listen backfill in at most 4 requests, the 30-listen sync, the deleted-user outcome and the chain stopping at `until_ts`
- [x] 5.2 Extend checkpoint tests for the `listenbrainz` provider (no regression on backward pages, two providers for one user, overlapping jobs); verify the new cases in `tests/test_import_checkpoints.py` pass alongside the existing Last.fm cases
- [x] 5.3 Define the disabled hourly sync schedule and confirm nothing else queues the import; verify `tests/test_job_schedules.py` lists it disabled and `tests/test_listenbrainz_jobs.py::test_linking_queues_nothing` passes

## 6. Sessions

- [x] 6.1 Add the `ListenSession` model and `listening.sessionize(db, user_id, since=None)` with the 30-minute gap, the `night-v1` rule, `unknown` without a timezone and deterministic rebuild; verify `tests/test_listen_sessions.py` covers gap splitting, extension of the last session, the sleep-tab, short-late and long-evening sessions, timezone missing then set, stable rebuild and user deletion
- [x] 6.2 Call `sessionize` from the import job for the stored time range; verify `tests/test_listenbrainz_jobs.py::test_import_extends_sessions` shows a sync extending the latest session
- [x] 6.3 Add `listen_session_overrides`, override re-application in `sessionize`, and the self-only session list and override routes; verify `tests/test_listen_sessions.py` covers keep-a-flagged-session, clear-an-override and rebuild-changes-boundaries, and `services/api/tests/test_session_overrides.py` covers the self-only policy

## 7. Operator command and docs

- [x] 7.1 Add `python -m sidetrack.listening` with `backfill`, `sync`, `import-export` and `sessionize`; verify `tests/test_listening_cli.py` covers job queuing output, the `account_not_linked` failure, in-process export import counts and `--rebuild`
- [x] 7.2 Write docs/LISTENING.md (linking the account, timezone, backfill, export import, sessions, what the counts mean) and update docs/JOBS.md with the new task and limit; verify the documented commands run as written against a local database
- [ ] 7.3 Run the owner's import for real (export or backfill), then `sessionize`, and record the counts (fetched, stored, duplicate, skipped, without release, sessions, night sessions) in docs/LISTENING.md, aggregates only; verify `GET /users/{id}/listening/recent` returns imported rows
- [ ] 7.4 Update `docs/status.yaml` ("ListenBrainz import" to works with evidence, "Listen storage" note), run `python scripts/gen_status.py` and `uv run --frozen python scripts/gen_progress.py`; verify the status check passes, then `make lint` and `make test.unit`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
- `resolve-listens-to-audio` depends on this change's imported tracks and session classifications; `add-weekly-listening-profile` reads the effective classification and import coverage.
