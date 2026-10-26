# Design

## Context

See proposal.md. Routes call `db.commit()` and, on `IntegrityError`, `db.rollback()`; tests share one session per test via a dependency override.

## Goals / Non-Goals

**Goals:** production-equivalent database in tests; migrations exercised on every run; fast enough for every PR.

**Non-Goals:** parallel test execution; per-test databases.

## Decisions

**One database per session, migrated once.** A session-scoped fixture resolves the URL (env var, else testcontainers), runs `alembic upgrade head` programmatically against it, and yields an engine. Migrating once keeps the suite fast; per-test isolation comes from transactions.

**Savepoint-joined sessions.** Each test opens a connection and an outer transaction, and binds the session with `join_transaction_mode="create_savepoint"`. A route's `commit()` releases a savepoint and its `rollback()` returns to one, and the outer transaction is rolled back after the test. This is SQLAlchemy 2.0's documented pattern for joining a session to an external transaction.

**Service container in CI, testcontainers locally.** GitHub's Postgres service avoids Docker-in-Docker startup cost and is the standard Actions pattern. Locally, testcontainers needs only Docker Desktop. Both use the same image tag as `deploy/stack.yml`.

**Drift test via `alembic.autogenerate.compare_metadata`.** It runs against the migrated database with `compare_type=True` and `compare_server_default=False`; server defaults are noisy across versions and none matter to the app yet.

## Risks / Trade-offs

- [Local runs now need Docker] → Docker Desktop is already required for compose. `SIDETRACK_TEST_DATABASE_URL` covers other setups.
- [Existing drift makes the new test fail immediately] → That's the point; fix it with a migration in this change if it's small.
- [The testcontainers image pull is slow the first time] → It happens once per machine; CI uses the service container.
