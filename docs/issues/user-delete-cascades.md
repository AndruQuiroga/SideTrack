# User deletion fails with existing listens

Filed with owner approval: https://github.com/AndruQuiroga/SideTrack/issues/286.

Phase 2 checkpoint tests exposed an existing identity deletion bug. Calling
`db.delete(User)` with persisted listens makes SQLAlchemy update
`listen_events.user_id` to NULL, violating its NOT NULL constraint, rather than
allowing the database's ON DELETE CASCADE. The user DELETE API uses this path.

Related spec: `listening/import-checkpoints`, requirement "Replays and competing
imports are safe", in the `replace-rq-with-postgres-jobs` change. Its user-deletion
scenario requires checkpoint cascade and prevents queued jobs from resurrecting
deleted data. The database cascade and deleted-job behavior can be verified
independently; the existing user-deletion API defect needs its own change.

Reproduce on migrated Postgres 16: persist a user, track and listen, delete the
user through the ORM, then flush. Expected: configured database cascades remove
dependent rows. Actual: NotNullViolation on listen_events.user_id.

Fix in a separate OpenSpec change, reviewing identity's deletion relationships
and adding an API regression with dependent rows. No identity fix is included
silently in the Phase 2 infrastructure change.
