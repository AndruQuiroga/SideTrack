# Spec Delta

## Purpose

Finds candidate shifts in a listener's analyzed listening over time, treating missing history as gaps, checking stability against a simple baseline, and showing the tracks behind every shift.

## ADDED Requirements

### Requirement: Weekly signals use eligible weeks only
For each user week, the eras job SHALL compute a play-weighted and an equal-track centroid of current embeddings over included plays with `audio_for_track` status `ok`, and an artist play-share vector, only when the weekly profile would not report `not_enough_listening`. Other weeks SHALL be stored as gaps with a reason, never as zero vectors.

#### Scenario: Eligible week
- **WHEN** a week has 84 included plays of which 61 have usable audio
- **THEN** the week's signal is computed from those 61 plays and records 61 as its sample

#### Scenario: Thin week is a gap
- **WHEN** a week has 12 included plays with usable audio
- **THEN** the week is stored as a gap with reason `not_enough_listening` and no signal

#### Scenario: Unimported week is a gap
- **WHEN** a week lies outside the user's import coverage
- **THEN** the week is stored as a gap with reason `not_imported`

#### Scenario: Autoplay plays excluded
- **WHEN** a week's only listening in one session has `effective_kind` `night_autoplay`
- **THEN** those plays do not contribute to the week's signal

### Requirement: Long gaps split the timeline
A run of at least 8 consecutive gap weeks SHALL split the history into segments. Change-point detection SHALL run within a segment only, and the gap SHALL be reported with its dates and reasons, never as a shift. The 8-week length SHALL be recorded as a product rule with the eras version.

#### Scenario: Import gap
- **WHEN** a user has eligible weeks in 2019 to 2021, 2 years of `not_imported` weeks and eligible weeks from 2024
- **THEN** the result has two segments and one gap with reason `not_imported`, and no candidate shift is placed at the gap

#### Scenario: Short gap inside a segment
- **WHEN** a segment contains 3 consecutive thin weeks
- **THEN** the segment is not split and those weeks are excluded from the detection input and listed as gaps

### Requirement: Candidate shifts need detector and baseline agreement
Within each segment, the job SHALL run an offline change-point search and a rolling-window baseline on the play-weighted signal. A candidate SHALL be reported only where both place a boundary within 2 eligible weeks of each other. The method, cost function, penalty, window and versions SHALL be stored with the result.

#### Scenario: Agreement
- **WHEN** the detector places a boundary at week 40 and the baseline at week 41
- **THEN** one candidate shift is reported at week 40 with both positions stored

#### Scenario: Detector-only boundary
- **WHEN** the detector places a boundary at week 70 and the baseline finds none within 2 weeks
- **THEN** no candidate is reported at week 70 and the stored diagnostics record the disagreement

### Requirement: Candidates must be stable
Each candidate SHALL be retested under week dropout, repeats collapsed to one play per track per week, and a parameter sweep, and SHALL record the fraction of variants that reproduce it within 2 eligible weeks. Candidates below a stability of 0.7 SHALL NOT be returned to users; the threshold SHALL be recorded with the eras version.

#### Scenario: One looped album
- **WHEN** a boundary exists only because one album was played 200 times in one week and disappears when repeats are collapsed
- **THEN** its stability is below 0.7 and it is not returned

#### Scenario: Stable shift
- **WHEN** a candidate reappears in 18 of 20 variants
- **THEN** it is returned with stability 0.9

### Requirement: Shifts show the tracks behind them
Each returned candidate SHALL list the tracks whose play share changed most between the 8 eligible weeks before and after it, with play counts in each window, and the number of plays with usable audio on each side. Each era SHALL list its most-played tracks. No candidate SHALL be returned without its evidence tracks.

#### Scenario: Review tracks
- **WHEN** the owner opens a candidate shift
- **THEN** the response lists tracks with before and after play counts and the usable-audio sample on each side

### Requirement: Shifts are described as hypotheses
The read model SHALL label each candidate as an estimated change in analyzed listening, with its method and stability. It SHALL NOT attach a life event, mood, feeling, personality, cause or diagnosis, and SHALL NOT name an era with a generated label.

#### Scenario: Response wording
- **WHEN** a candidate is returned
- **THEN** its fields contain dates, stability, method, evidence tracks and the fixed label `estimated_change`, and no free-text cause or emotion field

### Requirement: Eras are owner-only and gate-dependent
Era results SHALL be returned only to the user they describe; other callers SHALL receive 404. Until the evaluation register entry `listening-eras` is `approved`, results SHALL carry `validation: gate_pending`; when the entry is `rejected`, the read model SHALL return `rejected` and no candidates.

#### Scenario: Gate pending
- **WHEN** the owner requests eras and the gate entry is `gate_pending`
- **THEN** results are returned with `validation: gate_pending`

#### Scenario: Gate rejected
- **WHEN** the gate entry is `rejected`
- **THEN** the read model returns `rejected` with no candidate shifts

#### Scenario: Other member
- **WHEN** a club member requests another member's eras
- **THEN** they receive 404

### Requirement: Unavailable and insufficient states are explicit
The read model SHALL return `timezone_missing` without a timezone, `not_computed` before the first job, `stale_model` when stored signals use a model, checkpoint or pipeline other than current, and `insufficient_history` for a segment with fewer than 16 eligible weeks, in which no detection is run.

#### Scenario: Short history
- **WHEN** a user's only segment has 10 eligible weeks
- **THEN** that segment is returned with `insufficient_history` and no candidates

#### Scenario: Model changed
- **WHEN** the embedding pipeline version changes after the last eras job
- **THEN** the read model returns `stale_model` until the job reruns

### Requirement: Eras never acquire or serve audio
Era computation and responses SHALL use stored embeddings and listen metadata only. They SHALL NOT queue acquisition or yt-dlp, and SHALL NOT include audio, file paths or stream URLs.

#### Scenario: Response content
- **WHEN** an eras response is generated for a user whose history includes tracks without audio
- **THEN** it contains no audio, path or stream URL fields and no acquisition job is queued
