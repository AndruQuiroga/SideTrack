# Proposal

## Why

The API tests run on in-memory SQLite, while production runs Postgres 16 with Postgres-only types (`UUID`, `pg_insert ... ON CONFLICT`) and soon pgvector. The tests also build tables with `create_all`, so the Alembic migrations are never exercised: a model change without a migration passes CI and breaks the first deploy. Phase 0's gate requires CI to test on Postgres.

## What Changes

- The test database is Postgres 16 + pgvector (`pgvector/pgvector:pg16`, the production image). It comes from `SIDETRACK_TEST_DATABASE_URL` when set (CI uses a service container), otherwise from a throwaway testcontainers instance. There is no SQLite fallback.
- The test schema is built by `alembic upgrade head`, not `create_all`.
- A new test fails when the migrated schema and the SQLAlchemy models disagree (Alembic autogenerate comparison).
- Each test runs in a transaction rolled back afterwards; route-level commits and rollbacks use savepoints.
- CI's `python` job gets a Postgres service container.

### Out of scope

- Fixing any drift the new test finds beyond what's needed to make it pass. Drift found here is fixed with a migration in this change; larger model problems become their own change.
- Splitting unit and integration markers.

### Current state (observed)

- `services/api/tests/conftest.py:31-41`: SQLite in-memory engine with `Base.metadata.create_all`.
- `testcontainers[postgres,redis]==4.7.1` is already a dev dependency but unused.
- `.github/workflows/ci.yml` `python` job has no database.

## Capabilities

### New Capabilities

- `platform/schema-migrations`: guarantees that the Alembic migrations build the schema the application code expects, on the production database engine.

### Modified Capabilities

None.

## Impact

- `services/api/tests/conftest.py`, new `services/api/tests/test_migrations.py`, possibly a new migration under `migrations/versions/`
- `.github/workflows/ci.yml` (Postgres service)
- Local test runs need Docker, or `SIDETRACK_TEST_DATABASE_URL`
