# Spec Delta

## Purpose

Defines what Sidetrack's health endpoints report so Docker Swarm healthchecks and Uptime Kuma can detect a broken service and restart or alert on it.

## ADDED Requirements

### Requirement: Health reflects database reachability
`GET /health` SHALL return HTTP 200 when the API can query its database, and HTTP 503 when it cannot. The body SHALL name each checked dependency and its state, without connection strings or credentials.

#### Scenario: Database reachable
- **WHEN** the database answers a trivial query
- **THEN** `GET /health` returns 200 with `{"status": "ok", "details": {"database": "ok"}}`

#### Scenario: Database unreachable
- **WHEN** the database connection fails
- **THEN** `GET /health` returns 503 with `"status": "degraded"` and `"database": "unreachable"`
- **AND** the body does not contain the database URL

### Requirement: Health is cheap and unauthenticated
`GET /health` SHALL require no authentication and SHALL complete within 2 seconds even when the database is unreachable.

#### Scenario: Database hangs
- **WHEN** the database accepts connections but does not answer
- **THEN** `GET /health` returns 503 within 2 seconds
