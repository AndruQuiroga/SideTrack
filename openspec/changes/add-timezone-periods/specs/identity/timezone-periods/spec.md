# Spec Delta

## Purpose

Defines dated per-user timezone periods, so local-time analysis can read where a listener was at a
given moment instead of applying one zone to their whole history.

## ADDED Requirements

### Requirement: Users can have dated timezone periods

A user MAY have timezone periods, each with a start time and an IANA zone. A period SHALL apply from its start until the next period's start. Two periods for one user SHALL NOT share a start. An invalid zone name SHALL be refused.

#### Scenario: Period ends at the next one

- **WHEN** a user has periods starting in January in `America/Phoenix` and March in `America/New_York`
- **THEN** a moment in February resolves to `America/Phoenix`, and a moment in April to `America/New_York`

#### Scenario: Invalid zone

- **WHEN** a period is added with zone `Mars/Olympus`
- **THEN** it is refused and no period is stored

### Requirement: Zone lookup falls back to the user's timezone

For a moment before a user's first period, or for a user with no periods, the lookup SHALL return the user's `timezone`. With neither, it SHALL return no zone, and SHALL NOT guess one.

#### Scenario: Before the first period

- **WHEN** a user with timezone `America/New_York` has a first period in 2025 and a moment in 2021 is looked up
- **THEN** the result is `America/New_York`

#### Scenario: No zone anywhere

- **WHEN** a user has no periods and no timezone
- **THEN** the lookup returns no zone

### Requirement: Periods are operator-managed and don't rebuild by themselves

The operator command SHALL add, remove and list periods. Changing periods SHALL NOT change any session until sessions are rebuilt, and the command SHALL say a rebuild is needed.

#### Scenario: Adding a period

- **WHEN** the operator adds a period
- **THEN** existing sessions are unchanged, and the output says to rebuild sessions

### Requirement: Periods are deleted with the user

Deleting a user SHALL delete their timezone periods.

#### Scenario: User deleted

- **WHEN** a user with periods is deleted
- **THEN** none of their periods remain
