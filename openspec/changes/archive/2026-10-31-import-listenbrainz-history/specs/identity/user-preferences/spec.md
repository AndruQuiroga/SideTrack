# Spec Delta

## Purpose

Defines per-user preferences that other domains read when interpreting a user's data,
starting with the IANA timezone used for local-time analysis of listening.

## ADDED Requirements

### Requirement: Users have an optional IANA timezone
Each user MAY have a `timezone` holding an IANA zone name. The user update route SHALL accept it from the user or an admin, SHALL reject names that are not valid IANA zones, and SHALL return the stored value in user responses. A user without a timezone SHALL return `null`.

#### Scenario: Setting a valid timezone
- **WHEN** a user patches their own record with `timezone: "America/Phoenix"`
- **THEN** the response is 200 and later reads of the user return `timezone: "America/Phoenix"`

#### Scenario: Invalid zone name
- **WHEN** a user patches their record with `timezone: "Mars/Olympus"`
- **THEN** the response is 422 and the stored timezone is unchanged

#### Scenario: No timezone set
- **WHEN** a user who never set a timezone is read
- **THEN** the response has `timezone: null`

### Requirement: Other users cannot change a user's preferences
Only the user themselves or an admin SHALL change a user's timezone.

#### Scenario: Member edits another member
- **WHEN** a club member who is not an admin patches another user's `timezone`
- **THEN** the response is 403 and the other user's timezone is unchanged
