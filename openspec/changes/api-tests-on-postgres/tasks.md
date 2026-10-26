# Tasks

## 1. Test database

- [x] 1.1 Rewrite `services/api/tests/conftest.py`: session-scoped Postgres from `SIDETRACK_TEST_DATABASE_URL` or testcontainers (`pgvector/pgvector:pg16`), schema via `alembic upgrade head`, savepoint-joined sessions per test, and a clear error when no database is available. Verify the whole existing suite passes on Postgres (`make test.unit`).

## 2. Drift guard

- [x] 2.1 Add `services/api/tests/test_migrations.py` comparing the migrated schema with the models; fix any drift it reports. Verify it passes, and fails when a throwaway column is added to a model. Done: the drift (2 enum mappings, 12 indexes, 1 unique constraint, 1 FK) was in the models, so the models were fixed and no migration was needed. Detection is a committed test (`test_drift_check_detects_unmigrated_column`), and `test_listen_source_round_trips` reproduces the enum bug on the old model.

## 3. CI

- [x] 3.1 Add a `pgvector/pgvector:pg16` service to the CI `python` job and set `SIDETRACK_TEST_DATABASE_URL`. Verify with actionlint and a local run against an env-provided database (both pass); the PR's CI run confirms on GitHub.

## 4. Status

- [x] 4.1 Update `docs/STATUS.md` (Tests row) and `AGENTS.md` (tests need Docker or `SIDETRACK_TEST_DATABASE_URL`). Verify `pnpm exec openspec validate api-tests-on-postgres --strict` passes.
