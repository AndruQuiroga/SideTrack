# 0002: Postgres-backed job queue, no Redis

- Status: accepted
- Date: 2026-10-25

## Context

Background work ran on Redis + RQ (consumed by two processes) plus APScheduler, with sync cursors held in memory. Restarts lost state and duplicated work.

## Decision

Use a Postgres-backed queue (Procrastinate or PgQueuer; pick in the Phase 2 change) for all background and scheduled work. Cursors, schedules and outbox rows live in Postgres. Queues: `default`, `musicbrainz` (concurrency 1, rate-limited), `gpu` (consumed only on the GPU node).

## Consequences

- Redis, RQ and APScheduler are removed in Phase 2.
- Enqueueing can share a transaction with the data it acts on.
