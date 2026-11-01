# Spec Delta

## Purpose

Groups a user's embedded library into candidate sound-worlds and suggests descriptive terms from audio, without crowd tags. It abstains when no term is confident.

## ADDED Requirements

### Requirement: Themes are built per user and version
Theme building SHALL cluster the user's linked, embedded tracks with the configured algorithm version and parameters, and leave unclustered tracks unassigned. It SHALL record the algorithm, parameters, embedding revision, vocabulary version and input count. Rebuilding with the same inputs and seed SHALL give the same themes.

#### Scenario: Stable rebuild
- **WHEN** themes are built twice on unchanged data with the same seed
- **THEN** membership and suggested terms are identical

#### Scenario: Small library
- **WHEN** a user has fewer linked embedded tracks than the configured minimum
- **THEN** no themes are built and the result reports `not_enough_tracks` with the count

#### Scenario: Unassigned tracks are reported
- **WHEN** a build leaves 40 of 300 tracks unclustered
- **THEN** the result reports 40 unassigned tracks rather than forcing them into themes

### Requirement: Theme labels are suggestions with abstention
Each theme SHALL list up to three vocabulary terms ranked by the configured ranking method, and three representative tracks nearest its centre. Terms below the configured threshold SHALL be omitted. A theme with no qualifying term SHALL report `no_confident_label`. Scores SHALL NOT be presented as probabilities.

#### Scenario: Naming
- **WHEN** a theme's tracks rank 'melodic dubstep' above the threshold
- **THEN** 'melodic dubstep' is among its listed terms together with the ranking method version

#### Scenario: Abstention
- **WHEN** no vocabulary term passes the threshold for a theme
- **THEN** the theme reports `no_confident_label` and still lists its representative tracks

### Requirement: Users can rename themes
A user SHALL be able to set a display name for their theme, and the generated terms SHALL remain visible. After a rebuild, a rename SHALL carry over to the best-matching new theme when membership overlap meets the configured threshold. Otherwise it SHALL be reported as `rename_orphaned`.

#### Scenario: Rename
- **WHEN** the user renames a theme to 'late night sad'
- **THEN** reads return the new name and the original terms

#### Scenario: Rebuild breaks a theme
- **WHEN** a rebuild splits a renamed theme so no new theme meets the overlap threshold
- **THEN** the rename is reported as `rename_orphaned` and no new theme silently receives it
