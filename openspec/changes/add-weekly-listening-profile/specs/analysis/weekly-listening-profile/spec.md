# Spec Delta

## Purpose

Turns each week of included plays into a profile, described against the listener's own baseline, that states exactly which plays it rests on and which were excluded.

## ADDED Requirements

### Requirement: Profiles state their denominators and exclusions
Each weekly profile SHALL report:
- total plays and included plays;
- excluded plays per reason (such as autoplay or no timezone);
- included plays with usable audio;
- the probe, model and theme-build versions.

Mood and theme measures SHALL be play-weighted means over included plays with usable audio. Plays in sessions whose effective classification is autoplay SHALL be excluded and counted.

#### Scenario: Normal week
- **WHEN** a week has 100 plays, 16 in sessions classified autoplay, and 61 of the remaining 84 have scores
- **THEN** the profile reports 100 total, 84 included, 16 excluded as autoplay, 61 with audio, and mood is the play-weighted mean of those 61

#### Scenario: Override restores plays
- **WHEN** the user overrides an autoplay session to keep it and the profile is recomputed
- **THEN** that session's plays count as included and the excluded count drops accordingly

### Requirement: Thin weeks report unavailable
When fewer than 20 included plays have audio, mood and theme measures SHALL be reported as `not_enough_listening` and no value SHALL be given. The threshold SHALL be recorded as a product rule with the profile version.

#### Scenario: Thin week
- **WHEN** a week has 12 included plays with audio
- **THEN** mood is `not_enough_listening` and the coverage block is still returned

### Requirement: Values are baseline-relative
Each measure SHALL include a z-score against the user's previous 52 weeks that met the minimum. With fewer than 8 such weeks, the z-score SHALL be `no_baseline`. Weeks missing from history SHALL be skipped, never treated as zero.

#### Scenario: New user
- **WHEN** a user has 3 qualifying past weeks
- **THEN** z-scores are `no_baseline` while raw values are shown

#### Scenario: Gap in history
- **WHEN** the trailing 52 weeks include 10 weeks with no imported listens
- **THEN** the baseline uses only qualifying weeks and reports how many it used

### Requirement: Weeks follow the user's timezone
Weeks SHALL run from Monday 00:00 to Sunday 24:00 in the user's timezone, and the profile SHALL record the timezone used. Without a timezone, profiles SHALL NOT be computed and SHALL report `timezone_missing`. Changing the timezone SHALL recompute affected profiles.

#### Scenario: No timezone
- **WHEN** the user has no timezone
- **THEN** the profile job reports `timezone_missing`

#### Scenario: Timezone change
- **WHEN** the user changes timezone from UTC to America/Chicago
- **THEN** profiles are recomputed and record America/Chicago
