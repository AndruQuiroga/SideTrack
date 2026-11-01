# Spec Delta

## Purpose

Defines how a track's audio facets are returned by the API and shown on the track page, with
their provenance, analyzed coverage, distinct missing states and restricted wording, so a
listener can check every number against its method and input.

## ADDED Requirements

### Requirement: The facet route returns stored results with provenance
An authenticated read route SHALL return, for one catalog track, the asset used, its link method, and each facet's state, value with units, method, method version, analyzed span, asset kind and computed time, taken from stored results. It SHALL return 404 for an unknown track and SHALL NOT compute facets on request.

#### Scenario: Track with computed facets
- **WHEN** the owner requests facets for a track whose full asset has an available loudness result
- **THEN** the response lists loudness as `available` with value and unit LUFS, its method and version, its analyzed span and kind `full`

#### Scenario: Unknown track
- **WHEN** facets are requested for a track ID that does not exist
- **THEN** the route responds 404 and no facet job is queued

### Requirement: Missing states are distinct
The route and page SHALL distinguish `no_audio` (no linked asset), `ambiguous` (the track's audio link is ambiguous), `not_computed`, `failed`, `unavailable` with its reason, and `insufficient_sample` for a percentile. Each SHALL render as its own message, and none SHALL render a number, bar or default value.

#### Scenario: Track without audio
- **WHEN** the track page is opened for a track with no linked asset
- **THEN** the facet panel says no audio is linked for this track and shows no facet values

#### Scenario: Ambiguous audio link
- **WHEN** the audio-for-track lookup reports `ambiguous` for the track
- **THEN** the facet panel says the track's audio link is ambiguous and awaits review, and shows no facet values from any candidate asset

#### Scenario: Key unavailable
- **WHEN** a track's key result is `unavailable` with reason `weak_tonality`
- **THEN** the page shows key as unavailable with a plain-language reason and no tonic or mode

#### Scenario: Facet analysis failed
- **WHEN** a track's tempo result is `failed`
- **THEN** the page shows tempo analysis failed, distinct from not computed

### Requirement: Coverage and link certainty are shown
The facet panel SHALL show the analyzed span against the asset's duration, whether the asset is a preview or full track, and the track-to-asset link's method and whether an operator has confirmed it. Method name and version SHALL be available for every value without relying on hover alone.

#### Scenario: Preview-based facets
- **WHEN** a track's facets come from a 30-second preview
- **THEN** the panel states that values describe a 30-second preview, not the full track

#### Scenario: Link not confirmed
- **WHEN** the track's asset was linked by seed identity and no operator has confirmed the link
- **THEN** the panel names the link method and labels the link not confirmed

### Requirement: Tempo shows its alternatives
When a tempo result lists alternatives, the page SHALL show the primary tempo and its alternatives together as alternatives, not as one exact BPM.

#### Scenario: Ambiguous tempo
- **WHEN** a tempo result has primary 140 BPM and alternative 70 BPM
- **THEN** the page shows "140 or 70 BPM" with a note on half/double-time ambiguity

### Requirement: Percentiles name their reference
A facet percentile SHALL be shown only for the signed-in requesting user, phrased relative to "your eligible library" with its reference count. With `insufficient_sample`, the page SHALL show the absolute value with units and say there are too few analyzed tracks to compare.

#### Scenario: Percentile shown
- **WHEN** the signed-in user's brightness percentile is 82 with reference count 400
- **THEN** the page shows brighter than 82% of 400 tracks in your eligible library

#### Scenario: Too few tracks to compare
- **WHEN** the percentile is `insufficient_sample`
- **THEN** the page shows the centroid in Hz and states that there are too few analyzed tracks to compare, with no percentile

### Requirement: Facet wording is restricted
The page and API SHALL describe structure only as candidate boundaries and high-intensity segments, vocals only as an estimate of presence, and SHALL NOT show danceability, drop, build, breakdown, singer gender or any personality wording.

#### Scenario: Forbidden terms absent
- **WHEN** the track page renders every facet state in the web test fixtures
- **THEN** the rendered text contains none of danceability, drop, build-up, breakdown, male, female or gender

#### Scenario: Structure wording
- **WHEN** a structure result has a candidate boundary at 62 seconds
- **THEN** the page shows "candidate boundary at 1:02"

### Requirement: Facets never expose audio
Neither the route nor the page SHALL include audio URLs, file paths, playback controls or waveform data derived by streaming audio over HTTP.

#### Scenario: Response contains no audio location
- **WHEN** the facet route's response for any track is inspected
- **THEN** it contains no URL or path to an audio file and the page renders no audio element

### Requirement: Facet values are accessible without color
Every facet value and state SHALL be readable as text, available to keyboard and screen-reader users, and SHALL NOT rely on color alone to convey state or magnitude.

#### Scenario: State without color
- **WHEN** the facet panel renders an unavailable and an available facet
- **THEN** each state is expressed in text, not only by color
