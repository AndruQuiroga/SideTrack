# Spec Delta

## Purpose

Shows a listener their weekly profiles, themes, map and track analysis from stored values only, with sample sizes, distinct empty states and accessible alternatives.

## ADDED Requirements

### Requirement: Views render stored values with n
Every chart SHALL draw only stored values and show the included plays and audio coverage it rests on.

#### Scenario: Mood trail
- **WHEN** a user has 10 weekly profiles
- **THEN** the trail shows 10 points and each tooltip shows included plays and plays with audio

### Requirement: Insufficient data is explicit
A week reported as `not_enough_listening`, or missing from history, SHALL render as a gap with an explanation and SHALL never be interpolated. Distinct states (no audio, not computed, uncertain link, insufficient sample, stale model, failed) SHALL be shown with distinct text.

#### Scenario: Gap week
- **WHEN** one week in the range is `not_enough_listening`
- **THEN** that week is drawn as a gap with the explanation text and the line does not connect across it

#### Scenario: Stale model
- **WHEN** a track's mood was computed with an inactive probe version
- **THEN** the track page shows the stale-model state, not the old value

### Requirement: Maps are labelled projections with original-space neighbours
The taste galaxy SHALL show its projection version (model and revision, pipeline, corpus snapshot, method, parameters, seed) and a notice that distances and clusters on the map are distorted. Selecting a track SHALL list its nearest neighbours computed in the original vector space.

#### Scenario: Selecting a point
- **WHEN** the user selects a track on the galaxy
- **THEN** the neighbour list comes from original-space similarity and may include tracks that are far away on the map

#### Scenario: Projection label
- **WHEN** the galaxy renders
- **THEN** the projection version and the distortion notice are visible

### Requirement: Every chart has an accessible alternative
Each chart SHALL offer a table or list view with the same values, SHALL NOT use colour as the only way to distinguish information, SHALL be keyboard navigable, and SHALL respect the reduced-motion preference.

#### Scenario: Table view
- **WHEN** the user switches the theme river to its table view
- **THEN** each week's theme shares and n are listed as text, with gaps marked

#### Scenario: Reduced motion
- **WHEN** the browser reports `prefers-reduced-motion: reduce`
- **THEN** charts render without animated transitions

### Requirement: Personal views respect visibility
Mirror pages SHALL follow `listening_visibility`. Check-in data SHALL be shown only to its owner.

#### Scenario: Private user
- **WHEN** a member opens another member's private mirror
- **THEN** the page shows the private-listening notice and no data

#### Scenario: Public user's check-ins
- **WHEN** a member opens another member's public mirror
- **THEN** no check-in values or association view are shown
