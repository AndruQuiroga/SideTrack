# Proposal

## Why

Two defects predate the refactor and still break core features on main. Submitting a club rating returns 500, so "Ratings and summary" is **broken** in STATUS. Deleting a user who has any listening history fails, which GitHub issue #286 tracks. Both must be fixed before the first Stache-Rack rollout gives members access to these routes.

## What Changes

- **Rating submission works.** Observed: `sidetrack/club/routes/ratings.py:182` reads `payload.metadata`, but the schema field is `metadata_` with alias `metadata` (`sidetrack/schemas/core.py:243`), so every `POST /weeks/{week_id}/ratings` raises `AttributeError`. The route will store the submitted `metadata` in the rating's `metadata` column.
- **Rating and listen-event reads return the stored row.** Observed: `RatingRead` and `ListenEventRead` validate ORM rows with `from_attributes`, so the alias `metadata` resolves to SQLAlchemy's declarative `MetaData()` registry instead of the `metadata_` column (`sidetrack/listening/models.py:43`, `sidetrack/club/models.py:162`). Any response containing a listen event or rating row fails validation with a 500. These schemas will read the column, and the public JSON field stays named `metadata`.
- **User deletion uses the database cascades.** Observed: every foreign key to `users.id` is `ON DELETE CASCADE` in the migrations (`migrations/versions/0001_canonical_initial.py`), but `User.nominations`, `votes`, `ratings`, `listen_events`, `followers`, `following`, `compatibility_a` and `compatibility_b` (`sidetrack/identity/models.py:55-73`) declare no delete handling. SQLAlchemy therefore sets their `user_id` to NULL and violates NOT NULL before the database can cascade. `DELETE /users/{user_id}` (`sidetrack/identity/routes/users.py:139`) takes this path. The relationships will defer to the database cascades.
- Update `docs/status.yaml` and the two issue records, and drop the test-suite workaround in `services/api/tests/test_personal_access.py` that avoids returning listen events.

No API contract change: request and response field names and the OpenAPI schema stay the same. No migration: the database constraints are already correct.

## Capabilities

### New Capabilities
- `identity/account-deletion`: deleting a user removes the user and every row that the database cascades from it.
- `club/ratings`: a member's rating submission is stored and returned with its fields, including `metadata`.
- `listening/listen-events`: stored listen events are returned by the listen-event routes with their `metadata`.

### Modified Capabilities
None. `club/membership-access` and `identity/personal-data-visibility` govern who may call these routes. Their requirements don't change; only the outcome of an authorized call does.

## Out of scope

- Who may delete a user, rate, or read listens. That stays with ADR 0009 and is unchanged.
- Soft deletion, data export, or retaining club history after account deletion. Deleting a user also deletes their nominations, votes and ratings, as the existing constraints already specify.
- The 39-error mypy backlog, apart from errors in the lines this change edits.
- Week, album or track deletion behavior.

## Impact

- Code: `sidetrack/schemas/core.py`, `sidetrack/club/routes/ratings.py`, `sidetrack/identity/models.py`.
- Tests: new API regressions on migrated Postgres in `services/api/tests/` for each scenario. `test_personal_access.py` returns listen-event rows again.
- Docs: `docs/status.yaml` → `docs/STATUS.md`, `docs/issues/metadata-alias-crashes.md`, `docs/issues/user-delete-cascades.md`. Closes GitHub issue #286.
- No dependency, migration, client regeneration or deployment change.
