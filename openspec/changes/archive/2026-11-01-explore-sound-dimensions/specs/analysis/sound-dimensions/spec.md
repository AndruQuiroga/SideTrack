# Spec Delta

## Purpose

Defines how the audio lab finds the independent sound dimensions in a listener's own tracks,
checks that they're real and stable, relates them to mood, and records what the listener hears.

## ADDED Requirements

### Requirement: Dimensions use one vector per listener track

The analysis SHALL use one vector per track, preferring a full asset to a preview, and SHALL exclude listed control seeds. It SHALL report how many assets it dropped and why.

#### Scenario: Track with a full asset and a preview

- **WHEN** a track has both a full asset and a preview in the run
- **THEN** only the full asset's vector is used, and the preview is counted as dropped

#### Scenario: Control seeds listed

- **WHEN** a seed list names a track in the run
- **THEN** that track is left out, and the report counts it as excluded

### Requirement: Dimensions must beat a shuffled baseline

The analysis SHALL keep only components above the 95th percentile of the same data with each column shuffled independently.

#### Scenario: Planted structure

- **WHEN** synthetic vectors hold three planted directions
- **THEN** the analysis keeps three components

#### Scenario: Pure noise

- **WHEN** the vectors hold no structure
- **THEN** the analysis keeps no components and says so

### Requirement: Dimensions are checked for stability

Each kept component SHALL be compared across bootstrap resamples of tracks and reported with its stability value. Only stable components SHALL go to listening review. Runs with the same input and seed SHALL give the same result.

#### Scenario: Unstable component

- **WHEN** a component's median aligned cosine across resamples is below 0.80
- **THEN** it is reported as unstable and left out of the review

#### Scenario: Repeat run

- **WHEN** the analysis runs twice with the same input and seed
- **THEN** both results are identical

### Requirement: Overlap with mood is reported

For each reviewed axis the analysis SHALL report its correlation with valence and with arousal, and SHALL report the share of embedding variance the two mood scores explain on the same tracks.

#### Scenario: Axis restates mood

- **WHEN** an axis follows predicted arousal closely
- **THEN** the report shows the high correlation, and the axis stays available for review

#### Scenario: Predictions missing for a track

- **WHEN** a track has no mood prediction
- **THEN** it is left out of the overlap figures and counted

### Requirement: Suggested names can abstain

The analysis MAY suggest terms for each end of an axis from a versioned vocabulary. A term SHALL be suggested only above a permutation null, and an end with no such term SHALL report `no_confident_label`. No suggestion SHALL be presented as a fact about the music.

#### Scenario: No clear term

- **WHEN** no vocabulary term beats the null for an end of an axis
- **THEN** that end reports `no_confident_label`

#### Scenario: Text model unavailable

- **WHEN** the text tower can't load
- **THEN** suggestions report unavailable, and the rest of the analysis still completes

### Requirement: The listener judges dimensions blind

The review SHALL show tracks from each end of an axis without scores or suggested names, and SHALL record the listener's keep, merge or drop and their own name for each axis.

#### Scenario: Review page

- **WHEN** the review page is generated
- **THEN** it holds no scores or suggested names, and it needs no network or audio server

#### Scenario: Invalid decision file

- **WHEN** a decision file names an axis that isn't in the run
- **THEN** it is refused with the axis named

### Requirement: Personal results stay out of the repo

Track lists, per-track scores and the review page SHALL be refused inside the repository. Recorded results SHALL hold aggregates and the listener's axis names only.

#### Scenario: Output inside the repo

- **WHEN** an output path is inside the git working tree
- **THEN** the command fails and writes nothing
