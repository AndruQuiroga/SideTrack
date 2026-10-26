# 0002: Postgres-backed job queue, no Redis

- Status: accepted
- Date: 2026-10-25

## Context

Background work ran on Redis + RQ (consumed by two processes) plus APScheduler, with sync cursors held in memory. Restarts lost state and duplicated work.

## Decision

Use Procrastinate (selected in Phase 2, version 3.10.0) for background work.
Submission shares the caller's transaction through its psycopg connection.
Cursors, schedules and outbox rows live in Postgres. Queues: `default`,
`musicbrainz` (global execution lock and request pacing), `gpu` (dedicated worker).
The library schema is vendored and installed by Alembic; see docs/JOBS.md.

## Consequences

- Redis, RQ and APScheduler are removed; accepted RQ work must drain at cutover.
- Enqueueing can share a transaction with the data it acts on.
