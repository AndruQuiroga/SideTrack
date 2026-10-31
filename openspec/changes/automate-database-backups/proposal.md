# Proposal

## Why

Production now holds imported club history that cannot be rebuilt cheaply, but every Sidetrack database backup so far was taken by hand before a risky change. Nothing tells the owner when the site is down or when a backup stops happening.

Observed:
- `deploy/README.md` says backups are "Not automated yet", and `deploy/stack.yml` has no backup service.
- `deploy/SINGLES-GALLERY-2026-10-29.md` records a manual dump on the docker-1 HDD and a manual isolated restore. That procedure works, so this change schedules it.
- The latest rack records (stache-infra, 2026-10-29) list Uptime Kuma monitors for Sidetrack as still pending.

Observed on the rack, 2026-10-31 (read-only as the `aqui` user):
- The db task runs on docker-1, and the database is 10 MB with 10 weeks.
- `aqui` has no crontab entries, and the listed systemd timers include no backup job.
- `uptime-kuma_server` is 1/1, and answers from docker-1 through the Traefik VIP.
- `sudo` needs a password on docker-0 and docker-1.

Assumed: root has no crontab backing up this database, and Kuma can alert the owner. Task 1.1 confirms both before anything is installed.

## What Changes

- A daily database backup on docker-1 that writes a checksummed dump to `/srv/sidetrack/backups` and never publishes a partial file.
- Tiered retention that only removes files this job created, so manual dumps such as `sidetrack-pre-gallery-*` are never touched.
- A weekly restore check that restores the newest backup into a network-isolated, disposable Postgres 16 + pgvector container and checks schema and records.
- A copy of each backup on docker-0's HDD, so losing the docker-1 host does not lose every backup.
- Heartbeats to Uptime Kuma: a missed backup, failed restore check or failed copy alerts the owner.
- Uptime Kuma monitors for the public API health route and the LAN web hostname.
- The scripts and systemd units live in `deploy/backups/`, are tested in CI, and are installed by hand as the runbook describes.

Out of scope:
- Off-site or cloud copies. Both copies remain in the owner's home rack.
- Backing up audio files or the model cache. Audio can be fetched or copied again, and embeddings live in the database.
- Automatic restore into production. Restoring stays a deliberate operator step.
- Rack-wide backups for other services.
- Encrypting provider tokens at rest, which remains separate Phase 3 work.

## Capabilities

### New Capabilities
- `platform/database-backups`: scheduled, verified Postgres backups, retention, the off-host copy and restore checks.
- `platform/service-monitoring`: what is watched from outside the stack and how a failure reaches the owner.

### Modified Capabilities
None.

## Impact

- New files: `deploy/backups/`, `tests/test_database_backups.py`.
- Updated docs: `deploy/README.md`, `docs/status.yaml`, and the stache-infra backup and service pages.
- Rack: host-level systemd units and a root-only configuration file on docker-1, plus a restricted copy path to docker-0.
- No new Swarm service, image or stateful service, so no ADR is needed. Postgres stays the only stateful service.
- No API, schema or application changes.
