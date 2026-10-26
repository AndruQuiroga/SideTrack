# Design

## Context

See proposal.md for the observed defects. Two constraints shape the fix:

- **The column can't be called `metadata` on the model.** SQLAlchemy's declarative base reserves the name `metadata` for its `MetaData` registry. So the ORM attribute is `metadata_`, mapped to the `metadata` column, and the Pydantic schemas expose it under the alias `metadata`. With `from_attributes=True` and `populate_by_name=True` (`OrmSchema`, `sidetrack/schemas/core.py:19`), Pydantic looks the attribute up by alias first and finds the registry.
- **The database already cascades user deletes.** Every foreign key to `users.id` declares `ON DELETE CASCADE`, except `background_jobs.requested_by_user_id`, which is `SET NULL`. The ORM relationships on `User` don't declare that the database owns those deletes, so the unit of work issues `UPDATE … SET user_id = NULL` first.

## Goals / Non-Goals

**Goals:**
- Fix both defects without changing the OpenAPI contract or the generated TypeScript client.
- Make each spec scenario a Postgres-backed API test.

**Non-Goals:**
- Renaming the database column or the ORM attribute.
- Changing which relationships the ORM loads, apart from delete handling.

## Decisions

### 1. Read `metadata_` explicitly when validating from ORM objects

Add a small mixin, used by `RatingBase` and `ListenEventBase`, with a `model_validator(mode="before")`. When the input isn't a dict, it builds a dict from the model's field names (`metadata_` included) read off the ORM object. Dict input (request bodies) passes through unchanged, so `{"metadata": …}` still validates via the alias. This follows the existing before-validator on `LinkedAccountRead` (`core.py:96`).

Alternatives considered:
- `validation_alias=AliasChoices("metadata_", "metadata")`. Rejected: the OpenAPI request schema would advertise `metadata_` (the first choice), which changes the contract and the generated client.
- Renaming the ORM attribute. Rejected: `metadata` is reserved on the declarative base.
- Converting in every route. Rejected: the bug would come back in the next route that returns a row.

### 2. Fix the rating route's field access

`create_week_rating` passes `metadata_=payload.metadata_` to `Rating`. Today it passes `metadata=payload.metadata`. Even with a valid payload attribute, `Rating(metadata=…)` would quietly set the class-level registry name on the instance instead of the column, so the keyword has to be `metadata_`.

### 3. Defer user-owned collections to the database cascade

On `User`, set `passive_deletes="all"` on the collections owned by other domains: `nominations`, `votes`, `ratings`, `listen_events`, `followers`, `following`, `compatibility_a` and `compatibility_b`. With `"all"`, the ORM neither loads nor nulls those children on delete, and the database's `ON DELETE CASCADE` removes them in the same transaction.

The identity-owned collections (`linked_accounts`) and the analysis collections (`taste_profiles`, `recommendations`) already use `cascade="all, delete-orphan"`. They get `passive_deletes=True`, so unloaded rows are left to the database and aren't loaded first.

Alternatives considered:
- `cascade="all, delete-orphan"` on every collection. Rejected: identity would load and delete other domains' rows through the ORM, which works against the module ownership rule in MODULES.md and costs one query per collection.
- Deleting dependents in the route. Rejected: identity would need to write other domains' tables, which the import contracts forbid.

### 4. Tests

- `services/api/tests/test_account_deletion.py` covers the account-deletion scenarios. It builds dependents through each domain's models on migrated Postgres, calls the API, and then checks the rows with fresh queries.
- `services/api/tests/test_ratings.py` covers rating submission and reads.
- `services/api/tests/test_listen_events.py` covers the listen-event responses.
- The workaround comment in `test_personal_access.py` goes, and its listen-event tests assert the returned rows.
- An OpenAPI check confirms the `metadata` field name is unchanged in the rating and listen-event request and response schemas.

## Risks / Trade-offs

- [The test transaction wrapper could hide cascade behavior] → The deletion tests flush, expire the session, and query again inside the same Postgres transaction. `ON DELETE CASCADE` runs at statement time, so the check is real.
- [`passive_deletes="all"` leaves stale child objects in the session] → The route commits right after the delete, and commit expires all objects. No code reads a deleted user's collections afterwards.
- [Other schemas may use the same alias pattern] → Only `RatingBase` and `ListenEventBase` declare `metadata_` (`core.py:243`, `core.py:320`). The mixin is the documented way to add another.

## Migration Plan

No schema migration and no client regeneration. Deploying is an image update. Rolling back restores the old crashes and adds no data risk.
