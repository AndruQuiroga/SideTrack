# Spec Delta

## Purpose

Defines what watches Sidetrack from outside its own stack and how the owner learns that the service, or a scheduled safety job, has stopped working.

## ADDED Requirements

### Requirement: Service availability is monitored
The rack's monitoring service SHALL check the public API health route and the LAN web hostname at regular intervals, and SHALL alert the owner when either fails.

#### Scenario: API unhealthy
- **WHEN** `https://api.sidetrack.network/health` does not return 200 across the monitor's retry window
- **THEN** the monitor reports down and sends the owner an alert

#### Scenario: Service recovers
- **WHEN** a monitored endpoint returns to healthy
- **THEN** the monitor reports up and sends a recovery notice

### Requirement: Scheduled safety jobs report by heartbeat
The backup, off-host copy and restore-check jobs SHALL each send a heartbeat only after succeeding. A heartbeat that does not arrive inside its expected interval SHALL alert the owner, so a job that fails or never starts is treated the same way. A failed heartbeat request MUST NOT mark a successful backup as failed.

#### Scenario: Job does not run
- **WHEN** a scheduled job's heartbeat is missing past its interval and grace period
- **THEN** the monitor reports down and sends the owner an alert

#### Scenario: Job fails
- **WHEN** a job exits non-zero
- **THEN** no heartbeat is sent for that run

#### Scenario: Monitor unreachable
- **WHEN** a backup succeeds but its heartbeat request fails
- **THEN** the backup is kept and the job logs that the heartbeat was not delivered
