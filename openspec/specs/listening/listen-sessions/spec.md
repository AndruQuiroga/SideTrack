# listening/listen-sessions Specification

## Purpose
Defines how a user's listens are grouped into sessions, how likely sleep-tab autoplay
sessions are flagged by a reviewable heuristic, and how the user can confirm or reverse a
flag. Downstream analysis can then disclose which plays it excludes and why.

## Requirements

### Requirement: Listens are grouped into sessions by gap
The system SHALL group each user's listens, in played order, into sessions: a listen that starts more than 30 minutes after the previous listen begins a new session. Each session SHALL record its user, start, end and listen count, and every listen SHALL belong to exactly one session.

#### Scenario: Gap splits sessions
- **WHEN** a user has listens at 20:00, 20:04, 20:40 and 21:30
- **THEN** three sessions exist: one with the two listens at 20:00 and 20:04, one with the 20:40 listen, and one with the 21:30 listen

#### Scenario: New listens extend the last session
- **WHEN** a sync stores a listen 10 minutes after the end of the user's most recent session
- **THEN** that session's end and count are updated and no new session is created

### Requirement: Night autoplay sessions are flagged by rule
A session SHALL be flagged `night_autoplay` when, in the user's timezone, it starts between 22:00 and 04:00, lasts at least one hour and holds at least 12 listens. Every other session SHALL be `unclassified`, which SHALL NOT be read as evidence of deliberate listening. The rule version SHALL be recorded on each session, so a changed rule marks old flags stale.

#### Scenario: Sleep-tab session
- **WHEN** a session starts at 23:10 local time, ends at 02:40 and holds 40 listens
- **THEN** it is flagged `night_autoplay`

#### Scenario: Short late session
- **WHEN** a session starts at 23:10 local time, ends at 23:35 and holds 6 listens
- **THEN** it is flagged `unclassified`

#### Scenario: Long evening session
- **WHEN** a session starts at 20:30 local time, ends at 02:00 and holds 60 listens
- **THEN** it is flagged `unclassified`, because it did not start between 22:00 and 04:00

### Requirement: Users can review and reverse autoplay flags
A user SHALL be able to list their sessions with rule flags and set an override of `keep` (not autoplay) or `autoplay` on any session, or clear it. The effective classification SHALL be the override if one is set, otherwise the rule flag. Overrides SHALL be recorded with time and SHALL survive rebuilds while the session's start and end are unchanged.

#### Scenario: Keep a flagged session
- **WHEN** the user sets `keep` on a `night_autoplay` session
- **THEN** its rule flag stays `night_autoplay` and its effective classification is `keep`

#### Scenario: Clear an override
- **WHEN** the user clears the override
- **THEN** the effective classification returns to the rule flag

#### Scenario: Rebuild changes boundaries
- **WHEN** a rebuild changes an overridden session's start or end
- **THEN** the override is reported as `override_orphaned` and not applied to the new session

### Requirement: Sessions without a timezone carry no night flag
When the user has no timezone preference, sessions SHALL still be built and flagged `unknown`, and the sessionising result SHALL say that the timezone is missing. Setting the timezone and sessionising again SHALL replace `unknown` flags with `unclassified` or `night_autoplay`.

#### Scenario: Timezone missing
- **WHEN** sessions are built for a user without a timezone
- **THEN** every session is flagged `unknown` and the result reports `timezone_missing`

#### Scenario: Timezone set later
- **WHEN** the user's timezone is set and sessions are rebuilt
- **THEN** no session remains `unknown`

### Requirement: Sessions are rebuilt deterministically
Rebuilding a user's sessions from the same listens and rule version SHALL produce the same sessions, flags and applied overrides. Deleting the user SHALL delete the sessions and overrides.

#### Scenario: Rebuild is stable
- **WHEN** sessions are built twice for the same listens
- **THEN** the session boundaries, counts and flags are identical both times

#### Scenario: User deleted
- **WHEN** a user with sessions is deleted
- **THEN** none of their sessions remain
