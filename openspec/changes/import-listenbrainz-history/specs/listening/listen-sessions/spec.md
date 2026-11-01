# Spec Delta

## Purpose

Defines how a user's listens are grouped into sessions and how sleep-tab autoplay sessions
are told apart from active listening, so downstream analysis can weight chosen plays and
leave the service's choices out.

## ADDED Requirements

### Requirement: Listens are grouped into sessions by gap
The system SHALL group each user's listens, in played order, into sessions: a listen that starts more than 30 minutes after the previous listen begins a new session. Each session SHALL record its user, start, end and listen count, and every listen SHALL belong to exactly one session.

#### Scenario: Gap splits sessions
- **WHEN** a user has listens at 20:00, 20:04, 20:40 and 21:30
- **THEN** three sessions exist: one with the two listens at 20:00 and 20:04, one with the 20:40 listen, and one with the 21:30 listen

#### Scenario: New listens extend the last session
- **WHEN** a sync stores a listen 10 minutes after the end of the user's most recent session
- **THEN** that session's end and count are updated and no new session is created

### Requirement: Night autoplay sessions are flagged by rule
A session SHALL be flagged `night_autoplay` when, in the user's timezone, it starts between 22:00 and 04:00, lasts at least one hour and holds at least 12 listens. Every other session SHALL be `active`. The rule version SHALL be recorded on each session so a changed rule marks old flags stale.

#### Scenario: Sleep-tab session
- **WHEN** a session starts at 23:10 local time, ends at 02:40 and holds 40 listens
- **THEN** it is flagged `night_autoplay`

#### Scenario: Short late session
- **WHEN** a session starts at 23:10 local time, ends at 23:35 and holds 6 listens
- **THEN** it is flagged `active`

#### Scenario: Long evening session
- **WHEN** a session starts at 20:30 local time, ends at 02:00 and holds 60 listens
- **THEN** it is flagged `active`, because it did not start between 22:00 and 04:00

### Requirement: Sessions without a timezone carry no night flag
When the user has no timezone preference, sessions SHALL still be built and flagged `unknown`, and the sessionising result SHALL say that the timezone is missing. Setting the timezone and sessionising again SHALL replace `unknown` flags with `active` or `night_autoplay`.

#### Scenario: Timezone missing
- **WHEN** sessions are built for a user without a timezone
- **THEN** every session is flagged `unknown` and the result reports `timezone_missing`

#### Scenario: Timezone set later
- **WHEN** the user's timezone is set and sessions are rebuilt
- **THEN** no session remains `unknown`

### Requirement: Sessions are rebuilt deterministically
Rebuilding a user's sessions from the same listens and rule version SHALL produce the same sessions and flags. Deleting the user SHALL delete the sessions.

#### Scenario: Rebuild is stable
- **WHEN** sessions are built twice for the same listens
- **THEN** the session boundaries, counts and flags are identical both times

#### Scenario: User deleted
- **WHEN** a user with sessions is deleted
- **THEN** none of their sessions remain
