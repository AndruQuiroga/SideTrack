# Design

## Context

See proposal.md - Why. Relevant constraints:

- ADR 0006 pins Postgres to the node labelled `sidetrack.db=true`, which is docker-1. `/srv/sidetrack/backups` there is a dedicated HDD, physically separate from the database SSD but on the same host.
- docker-0 is on a different physical host and has a separate HDD mounted at `/mnt/sidetrack-hdd`.
- AGENTS.md forbids new services without an ADR. Postgres remains the only stateful service.
- Portainer is the stack's only writer, so backup work must not change the stack.
- Agent SSH runs as `aqui`, and `sudo` needs a password on both hosts. Passwordless sudo must not be granted automatically (stache-infra SSH access guide), so anything needing root is run by the owner in an interactive terminal.
- `/srv/sidetrack/audio` and `/srv/sidetrack/backups` are symlinks into root-only HDD mounts, so `aqui` can't inspect them directly.
- Everything is authored and tested in the repo first.

## Goals / Non-Goals

**Goals:**
- A missed or broken backup becomes visible within a day.
- A backup only counts once a restore has proved the format works.
- Rack changes are small, reversible and described in the runbook.

**Non-Goals:**
- Point-in-time recovery. Losing up to a day of club activity is acceptable for this project.
- Moving backup logic into the application or job queue.

## Decisions

### 1. A host systemd timer, not a Swarm service

The job runs as systemd units on docker-1 and reaches Postgres with `docker exec` into the running db task, as the manual procedure does.

Alternatives: a cron container in the stack would be a new service needing an ADR and Portainer changes, and needs the Docker socket or a database password. A Procrastinate task would mean a failing application or database also stops the thing reporting on it. The timer has neither problem, and `Persistent=true` runs a missed backup after downtime.

### 2. Custom-format `pg_dump`

Use `pg_dump -Fc`, matching the latest manual backup, because it is compressed and supports selective restore. Backups are named `sidetrack-daily-<UTC timestamp>.dump`. That prefix is the retention boundary: `sidetrack-pre-*` and other manual dumps can never match it.

Writes go to a `.partial` file, then fsync, checksum and rename. The job checks with `findmnt` that the directory is on the expected source, because a missing mount would otherwise fill the root disk silently.

### 3. Retention by calendar bucket

The newest backup of each day, ISO week and month falls in the 7-daily, 4-weekly and 6-monthly sets. Anything in no set is removed. Retention is skipped if no new backup exists, so a broken job cannot age out good backups. At the current database size this stays small; task 1.1 confirms the size.

### 4. Off-host copy to docker-0

Copy over SSH, using a dedicated key that may only write into one directory on `/mnt/sidetrack-hdd`, with a forced `rrsync`-style command. The destination recomputes the SHA-256.

Alternatives: pushing to the workstation depends on it being on. A Proxmox vzdump covers the VM rather than the database and already exists as a manual recovery point. docker-0 is the cheapest copy that survives losing the docker-1 host, its HDD or stache-1. Both hosts share a building and power, so this is not an off-site copy.

**Owner to confirm before applying:** this adds SSH trust from docker-1 to docker-0. Group 4 of the tasks is separable; dropping it means removing the second-host requirement from the spec delta.

### 5. Weekly restore check in a disposable container

Run `pgvector/pgvector:pg16` with `--network none`, restore into it, and assert the `alembic_version` matches the expected head and `weeks` and `users` are non-empty. The expected head comes from the live database at check time, so migrations need no script change, while the restored data still has to match what production runs. A `trap` removes the container on every exit path.

### 6. Heartbeats through Uptime Kuma push monitors

Each job calls its own Kuma push URL only after succeeding. Push monitors catch the cases a failure hook cannot, such as a disabled timer or a dead host. URLs contain a token, so they live in a root-only `/etc/sidetrack/backup.env` and are never logged. Curl failures are logged and do not fail the job.

### 7. Bash, tested with fake commands

The scripts are POSIX-tool bash, so docker-1 needs nothing installed. `tests/test_database_backups.py` runs them on Linux CI against a temporary directory, with fake `docker`, `findmnt` and `curl` first on `PATH`, covering each spec scenario. A true restore is proved by a test using the suite's Postgres image, plus a real run on the rack.

## Risks / Trade-offs

- **Up to 24 hours of data can be lost.** Accepted; a manual dump before risky changes stays in the runbook.
- **Dumps hold live provider tokens.** Mitigation: root-only files on both hosts. The real fix is encrypting tokens at rest, which is separate work.
- **The stache-1 HDD is old.** Mitigation: the off-host copy and weekly checksum and restore checks.
- **The db task could move node.** It is pinned by label, and the job fails loudly if it finds no local db container, which the heartbeat then surfaces.
- **Host units sit outside Portainer.** Mitigation: the unit files live in this repo, and the stache-infra pages record what is installed.

## Open Questions

- The off-host copy in Decision 4 needs the owner's confirmation.
- Whether Kuma already has a notification channel that reaches the owner. Task 1.1 checks this, and the owner configures one if not.
