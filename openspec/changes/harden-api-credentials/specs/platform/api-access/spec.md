# Spec Delta

## Purpose

Defines how callers are authorized to change data through the Sidetrack API and what the API reveals when something goes wrong.

## ADDED Requirements

### Requirement: Writes require the service token
Every POST, PUT, PATCH and DELETE request SHALL carry `Authorization: Bearer <token>` matching the configured service token, except routes explicitly listed as public. Public write routes are `/integrations/lastfm/callback`, which is protected by its signed `state`.

#### Scenario: Missing or wrong token
- **WHEN** a client sends `POST /weeks/` without a bearer token, or with a wrong one
- **THEN** the API responds 401 and nothing is written

#### Scenario: Correct token
- **WHEN** a client sends `POST /weeks/` with the configured token
- **THEN** the request is processed normally

### Requirement: The API fails closed without a service token
Outside development mode, the API SHALL refuse to start when no service token is configured. Development mode is enabled only by `SIDETRACK_ENV=development`.

#### Scenario: Production start without a token
- **WHEN** the API starts with `SIDETRACK_API_TOKEN` unset and `SIDETRACK_ENV` unset or `production`
- **THEN** startup fails with an error naming `SIDETRACK_API_TOKEN`

#### Scenario: Development start without a token
- **WHEN** the API starts with `SIDETRACK_API_TOKEN` unset and `SIDETRACK_ENV=development`
- **THEN** the API starts, logs a warning that writes are unauthenticated, and accepts writes without a token

### Requirement: Error responses do not reveal internals
Responses to unhandled errors SHALL contain a generic message and a request ID, and SHALL NOT contain exception messages, stack traces, SQL or configuration values. The full error SHALL be logged with the same request ID.

#### Scenario: Unhandled exception
- **WHEN** a route raises an unexpected exception whose message contains a database URL
- **THEN** the response is 500 with body `{"error": "internal_server_error", "request_id": "<id>"}`
- **AND** the response body does not contain the database URL
- **AND** the server log contains the exception with the same request ID
