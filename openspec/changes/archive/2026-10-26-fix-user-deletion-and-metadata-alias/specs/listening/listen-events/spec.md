# Spec Delta

## Purpose

Defines how stored listen events are written and returned by the listen-event routes, so a user's listening history can be read back exactly as it was stored.

## ADDED Requirements

### Requirement: Listen-event responses return stored rows
`POST /listen-events/`, `GET /listen-events/` and `GET /listen-events/{id}` SHALL return each stored listen event with its user, track, played time, source, ingestion time and `metadata`, for callers allowed to see it. The public field name SHALL remain `metadata`. Listen events without metadata SHALL return `null`.

#### Scenario: Recording a listen with metadata
- **WHEN** a user posts a listen with `metadata` `{"device": "turntable"}`
- **THEN** the response is 201, and the returned listen has that `metadata` and the user as its `user_id`

#### Scenario: Listing own listens
- **WHEN** a user with two stored listen events calls `GET /listen-events/`
- **THEN** the response is 200 with both events, newest first, each with its stored `metadata`

#### Scenario: Reading one listen
- **WHEN** a user fetches `GET /listen-events/{id}` for their own listen event stored without metadata
- **THEN** the response is 200 and its `metadata` is `null`

#### Scenario: Reading a shared user's listens
- **WHEN** a club member lists `GET /listen-events/?user_id={id}` for another member who shares listening with the club and has a stored listen
- **THEN** the response is 200 and contains that listen
