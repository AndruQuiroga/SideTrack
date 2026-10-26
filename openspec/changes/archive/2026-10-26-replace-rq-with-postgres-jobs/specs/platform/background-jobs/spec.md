# Spec Delta

## Purpose

Keep accepted background work and schedules durable across process restarts using
Postgres, with observable results and explicit failure states.

## ADDED Requirements

### Requirement: Submission is transactional and durable
The system SHALL commit queued work to Postgres before reporting acceptance. Work submitted with domain changes MUST share their transaction. A rollback MUST leave neither the domain change nor its job visible.

#### Scenario: Restart after acceptance
- **WHEN** an ingest request returns 202 and API and worker processes restart
- **THEN** the returned job ID still identifies runnable or completed work

#### Scenario: Transaction rolls back
- **WHEN** a domain update and its job submission are rolled back
- **THEN** neither the update nor the job is visible to another connection

#### Scenario: Database cannot accept work
- **WHEN** job submission cannot commit because Postgres is unavailable
- **THEN** the API returns 503 without a job acceptance response

### Requirement: Existing callers can poll safe job results
The ingest and taste-profile submission endpoints SHALL retain their 202 response fields. GET /jobs/{job_id}/status SHALL retain job_id, status, result and error, with states queued, started, finished, failed, deferred and canceled. It MUST return 404 for unknown IDs and MUST NOT expose tracebacks, credentials or raw exception text.

#### Scenario: Completed job
- **WHEN** a caller polls a completed job after restarting the API
- **THEN** it receives finished and the persisted JSON result

#### Scenario: Failed or unknown job
- **WHEN** a caller polls an exhausted job or an unknown ID
- **THEN** it receives failed with a safe error code for the former and HTTP 404 for the latter

### Requirement: Execution has bounded retries and recovery
Jobs SHALL persist attempts and terminal status. Transient failures and stalled workers MUST be retried within a configured attempt limit. Graceful shutdown MUST stop new claims and allow bounded completion. Replayed jobs MUST NOT duplicate committed domain effects.

#### Scenario: Worker dies during execution
- **WHEN** a worker is terminated after claiming a job and before completing it
- **THEN** stalled-job recovery makes the job runnable again without duplicating committed effects

#### Scenario: Attempts exhausted
- **WHEN** a job reaches its configured attempt limit
- **THEN** it remains failed and is not automatically retried again

### Requirement: Queues isolate workloads
CPU workers SHALL consume default and musicbrainz work only. Musicbrainz jobs MUST run one at a time across worker processes and start web API requests at least one second apart globally. GPU jobs MUST only be consumed by an explicitly configured GPU worker. Unsupported task types MUST report unavailable instead of fabricated success.

#### Scenario: Multiple CPU workers
- **WHEN** two CPU workers receive default, musicbrainz and gpu jobs
- **THEN** default work can progress concurrently, musicbrainz work is globally serialized and rate-limited, and gpu work remains unclaimed

#### Scenario: Unimplemented GPU operation
- **WHEN** a caller requests an unimplemented GPU analysis operation
- **THEN** the system reports unavailable and produces no fabricated analysis result

### Requirement: Schedules survive restarts without duplicate occurrences
Enabled schedules and their next occurrence SHALL live in Postgres. Multiple scheduler processes MUST create at most one job per schedule occurrence. Restarting after downtime MUST coalesce missed recurring occurrences into one runnable occurrence and advance the stored deadline.

#### Scenario: Two schedulers restart after downtime
- **WHEN** two scheduler processes reconcile the same overdue recurring schedule
- **THEN** exactly one catch-up job is persisted and the next deadline is in the future

### Requirement: Postgres is the only queue service
The supported API, worker and bot deployment SHALL operate without Redis, RQ or APScheduler. Queue schema installation MUST be versioned and reproducible on Postgres 16 with pgvector. Legacy dormant worker startup MUST fail with an actionable retirement message rather than run unsupported Spotify jobs.

#### Scenario: Clean deployment
- **WHEN** migrations and supported services start against an empty Postgres database without Redis
- **THEN** an API-submitted job completes and its result can be polled

#### Scenario: Legacy worker startup
- **WHEN** an operator starts the retired services.worker runtime
- **THEN** it exits with instructions for the supported worker and does not schedule Spotify work
