# Tasks

## 1. Metadata on ratings and listen events

- [x] 1.1 Write the regressions first and confirm they fail on main. `services/api/tests/test_ratings.py` covers every scenario of `club/ratings`, and `services/api/tests/test_listen_events.py` covers every scenario of `listening/listen-events`. Run `uv run --frozen --extra api --extra dev pytest services/api/tests/test_ratings.py services/api/tests/test_listen_events.py` and record the 500s.
- [x] 1.2 Add the ORM-metadata before-validator mixin in `sidetrack/schemas/core.py` and apply it to `RatingBase` and `ListenEventBase`. Change `create_week_rating` to pass `metadata_=payload.metadata_`. Verify both test files from 1.1 pass.
- [x] 1.3 Remove the serialization workaround comment in `services/api/tests/test_personal_access.py`. Make `test_unfiltered_listen_event_list_is_own` also assert the actor's own listen row, and verify the file passes.
- [x] 1.4 Assert the contract is unchanged. A test in `services/api/tests/test_ratings.py` checks that the OpenAPI schemas for `RatingCreate`, `RatingRead`, `ListenEventCreate` and `ListenEventRead` name the field `metadata` and not `metadata_`. Also verify `tests/test_job_compatibility.py` and `tests/test_module_layout.py` (the API snapshot checks) still pass.

## 2. User deletion

- [x] 2.1 Write `services/api/tests/test_account_deletion.py` covering every scenario of `identity/account-deletion`, including a listen event, an import checkpoint, a nomination, a vote, a rating, follows in both directions, a compatibility row and club membership. Confirm it fails on main with `NotNullViolation`.
- [x] 2.2 Set `passive_deletes="all"` on `User.nominations`, `votes`, `ratings`, `listen_events`, `followers`, `following`, `compatibility_a` and `compatibility_b`, and `passive_deletes=True` on `linked_accounts`, `taste_profiles` and `recommendations`, in `sidetrack/identity/models.py`. Verify `test_account_deletion.py` passes. Verify `services/api/tests/test_migrations.py` still reports no model/migration drift and `tests/test_import_checkpoints.py` still passes.

## 3. Status and integration

- [x] 3.1 Update `docs/status.yaml`. "Ratings and summary" moves to **works**, with `services/api/tests/test_ratings.py` as evidence. "User deletion with listening history" moves to **works**, with `services/api/tests/test_account_deletion.py`. Regenerate `docs/STATUS.md` and verify `scripts/gen_status.py --check` passes.
- [x] 3.2 Mark `docs/issues/metadata-alias-crashes.md` and `docs/issues/user-delete-cascades.md` as resolved by this change, and verify the evidence paths they cite exist.
- [x] 3.3 Run the full checks: `lint-imports`, `ruff check`, `mypy` (no errors beyond the 39 recorded), `pytest -m "unit and not slow and not gpu"`, the full `services/api/tests` suite on migrated Postgres, and `pnpm exec openspec validate fix-user-deletion-and-metadata-alias --strict`.

## Workflow follow-up

- Close GitHub issue #286 when the PR merges, linking `test_account_deletion.py`.
- Archive the change and regenerate `docs/STATUS.md` and the progress artifact.
