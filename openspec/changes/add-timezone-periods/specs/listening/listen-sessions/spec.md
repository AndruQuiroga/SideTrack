# Spec Delta

## MODIFIED Requirements

### Requirement: Night autoplay sessions are flagged by rule

A session SHALL be flagged `night_autoplay` when, in the zone in force for the user at its start, it starts between 22:00 and 04:00, lasts at least one hour and holds at least 12 listens. Every other session SHALL be `unclassified`, which SHALL NOT be read as evidence of deliberate listening. The rule version SHALL be recorded on each session, so a changed rule marks old flags stale.

#### Scenario: Sleep-tab session

- **WHEN** a session starts at 23:10 local time, ends at 02:40 and holds 40 listens
- **THEN** it is flagged `night_autoplay`

#### Scenario: Short late session

- **WHEN** a session starts at 23:10 local time, ends at 23:35 and holds 6 listens
- **THEN** it is flagged `unclassified`

#### Scenario: Long evening session

- **WHEN** a session starts at 20:30 local time, ends at 02:00 and holds 60 listens
- **THEN** it is flagged `unclassified`, because it did not start between 22:00 and 04:00

#### Scenario: Same clock time across a move

- **WHEN** a user's zone changes between two sessions that start at the same UTC hour
- **THEN** each session is classified by the zone in force at its own start

### Requirement: Sessions without a timezone carry no night flag

When no zone is in force for a session's start, sessions SHALL still be built and flagged `unknown`, and the sessionising result SHALL say that the timezone is missing. Setting the timezone and sessionising again SHALL replace `unknown` flags with `unclassified` or `night_autoplay`.

#### Scenario: Timezone missing

- **WHEN** sessions are built for a user without a timezone
- **THEN** every session is flagged `unknown` and the result reports `timezone_missing`

#### Scenario: Timezone set later

- **WHEN** the user's timezone is set and sessions are rebuilt
- **THEN** no session remains `unknown`
