# Spec Delta

## Purpose

Groups a user's embedded library into recurring sound-worlds and names them from audio, without crowd tags.

## ADDED Requirements

### Requirement: Themes are built per user and version
Theme building SHALL cluster the user's linked, embedded tracks, keep clusters of at least 8 tracks, record the algorithm version and leave the rest unassigned. Rebuilding with the same inputs SHALL give the same themes.

#### Scenario: Stable rebuild
- **WHEN** themes are built twice on unchanged data
- **THEN** membership and names are identical

#### Scenario: Small library
- **WHEN** a user has fewer than 8 embedded tracks
- **THEN** no themes are built and the result reports `not_enough_tracks`

### Requirement: Themes are named by calibrated terms
Each theme SHALL list its top three vocabulary terms ranked by similarity z-scored across the library, and three representative tracks nearest its centre.

#### Scenario: Naming
- **WHEN** a theme's tracks are closest to 'melodic dubstep' after calibration
- **THEN** 'melodic dubstep' is among its listed terms

### Requirement: Users can rename themes
A user SHALL be able to set a display name for their theme; the generated terms SHALL remain visible.

#### Scenario: Rename
- **WHEN** the user renames a theme to 'late night sad'
- **THEN** reads return the new name and the original terms
