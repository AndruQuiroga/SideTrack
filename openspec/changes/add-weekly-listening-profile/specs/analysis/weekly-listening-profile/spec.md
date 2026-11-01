# Spec Delta

## Purpose

Turns each week of chosen plays into a profile described against the listener's own baseline, with the data it rests on.

## ADDED Requirements

### Requirement: Profiles use chosen plays with audio
A week's profile SHALL be computed from plays outside night-autoplay sessions whose tracks have current mood scores, weighted by play count, and SHALL report chosen plays, plays with audio and the probe version.

#### Scenario: Normal week
- **WHEN** a week has 84 chosen plays and 61 with scores
- **THEN** the profile reports 61 of 84 and mood is the play-weighted mean of those 61

### Requirement: Thin weeks report unavailable
When fewer than 20 chosen plays have audio, mood and themes SHALL be reported `not_enough_listening` and no value SHALL be given.

#### Scenario: Thin week
- **WHEN** a week has 12 chosen plays with audio
- **THEN** mood is `not_enough_listening`

### Requirement: Values are baseline-relative
Each measure SHALL include a z-score against the user's previous 52 weeks that met the minimum; with fewer than 8 such weeks the z-score SHALL be `no_baseline`.

#### Scenario: New user
- **WHEN** a user has 3 qualifying past weeks
- **THEN** z-scores are `no_baseline` while raw values are shown

### Requirement: Weeks follow the user's timezone
Weeks SHALL run Monday 00:00 to Sunday 24:00 in the user's timezone; without one, profiles SHALL not be computed and report `timezone_missing`.

#### Scenario: No timezone
- **WHEN** the user has no timezone
- **THEN** the profile job reports `timezone_missing`
