# Spec Delta

## Purpose

Shows a listener their weekly profiles, themes and track analysis from stored values only, with sample sizes and explicit empty states.

## ADDED Requirements

### Requirement: Views render stored values with n
Every chart SHALL draw only stored values and show the plays and audio coverage it rests on.

#### Scenario: Mood trail
- **WHEN** a user has 10 weekly profiles
- **THEN** the trail shows 10 points and each tooltip shows chosen plays and plays with audio

### Requirement: Insufficient data is explicit
A week reported `not_enough_listening` SHALL render as a gap with an explanation, never interpolated.

#### Scenario: Gap week
- **WHEN** one week in the range is `not_enough_listening`
- **THEN** that week is drawn as a gap with the explanation text

### Requirement: Personal views respect visibility
Mirror pages SHALL follow `listening_visibility`.

#### Scenario: Private user
- **WHEN** a member opens another member's private mirror
- **THEN** the page shows the private-listening notice and no data
