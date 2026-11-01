# Spec Delta

## Purpose

Defines how Sidetrack computes interpretable audio facets (tempo, key, loudness, brightness,
band energy, vocal presence and candidate structure) for each audio asset, records their
method, input coverage and state, and expresses them relative to a listener's own library.

## ADDED Requirements

### Requirement: Facets are stored per asset with provenance
Each stored facet result SHALL belong to one audio asset and one facet, and record the method name, method version, decoding pipeline version, analyzed start and end in seconds, the asset's kind (full or preview), the state, the job that produced it and when. An asset SHALL have at most one result per facet and method version.

#### Scenario: Loudness computed for a full track
- **WHEN** a facet job computes loudness for a 312-second full-track asset analyzed in full
- **THEN** one loudness row exists for the asset with state `available`, method and version, analyzed span 0 to 312 seconds, kind `full`, the job ID and a timestamp

#### Scenario: Duplicate result rejected
- **WHEN** a second row for the same asset, facet and method version is written
- **THEN** the database rejects it and one row remains

### Requirement: Facet states are explicit and never faked
A facet result SHALL have exactly one state: `available` with a value, `failed` with a reason code, or `unavailable` with a reason code. An asset with no row for a facet SHALL be reported as `not_computed`. `failed` and `unavailable` rows SHALL carry no value, and no code path MAY store a default, constant, random or placeholder value.

#### Scenario: Method libraries missing
- **WHEN** a tempo job runs where the tempo method's libraries cannot be imported
- **THEN** the job fails with error `unavailable`, and no tempo rows with values are written

#### Scenario: Not computed
- **WHEN** facets are read for an asset that no facet job has processed
- **THEN** every facet is reported `not_computed` and no value is returned

### Requirement: Only reviewed methods are enabled
Facet jobs SHALL run only methods on the enabled facet-method list. A method SHALL be added to that list only with a recorded audio-lab facet run, a license review covering its code, weights and runtime dependencies, and the owner's recorded decision. Requesting any other method SHALL fail before a job is queued, naming the enabled methods.

#### Scenario: Method not enabled
- **WHEN** the operator runs the facet command for a key method that is not on the enabled list
- **THEN** the command exits non-zero naming the enabled key methods, and no job is queued

#### Scenario: Enabled list matches the review record
- **WHEN** the enabled facet-method list is compared with the license review table in docs/AUDIO-FACETS.md
- **THEN** every enabled method has a row marked accepted with its code, weights and dependency licenses

### Requirement: Tempo reports alternatives and beats
An available tempo result SHALL contain a primary tempo in BPM, the half- and double-tempo alternatives when the method or beat sequence supports them, the beat timestamps it was estimated from, and the method's ambiguity indicator. A tempo SHALL NOT be reported without the beat sequence that produced it.

#### Scenario: Half/double-time ambiguity
- **WHEN** a click track with clicks every 0.857 seconds and accents on every second click is analyzed
- **THEN** the result lists 70 and 140 BPM as primary and alternative tempi in either order, and includes beat timestamps

#### Scenario: No beats found
- **WHEN** a recording of sustained noise with no onsets is analyzed
- **THEN** the tempo result is `unavailable` with reason `no_beats`, and no BPM is stored

### Requirement: Key estimates may be unavailable
An available key result SHALL contain a tonic, a mode and the method's strength value. When the strength is below the method's documented threshold, or the method reports no tonal centre, the result SHALL be `unavailable` with reason `weak_tonality` rather than a guessed key.

#### Scenario: Clear tonal input
- **WHEN** a synthesized A minor chord progression is analyzed
- **THEN** the result is `available` with tonic A and mode minor, and a strength value

#### Scenario: Atonal input
- **WHEN** white noise is analyzed
- **THEN** the key result is `unavailable` with reason `weak_tonality` and has no tonic or mode

### Requirement: Loudness follows EBU R 128
Loudness SHALL report integrated loudness in LUFS and loudness range in LU, measured as specified by EBU R 128, ITU-R BS.1770 and EBU Tech 3342, from the asset's decoded channels rather than the embedding pipeline's mono downmix. The result SHALL record the analyzed span and whether it was capped.

#### Scenario: Reference tone
- **WHEN** a 20-second stereo 1 kHz sine at -23 dBFS per channel is analyzed
- **THEN** the integrated loudness is -23.0 LUFS within 0.1 LU

#### Scenario: Too short to measure
- **WHEN** an asset shorter than the 3-second short-term window is analyzed for loudness range
- **THEN** loudness range is `unavailable` with reason `too_short`

### Requirement: Brightness and band energy are stated measurements
Brightness SHALL be reported as the median spectral centroid in Hz with its frame size and hop. Band energy SHALL be reported as the share of spectral energy within each stated frequency band, including a named bass band with its edges in Hz. Neither SHALL be labelled as a complete description of timbre.

#### Scenario: Low and high tones
- **WHEN** a 100 Hz sine and a 4 kHz sine are analyzed
- **THEN** the 100 Hz signal's centroid is lower than the 4 kHz signal's, and its bass-band share is above 0.9

### Requirement: Vocal presence is an estimate without identity
Vocal presence SHALL be reported as one of `likely_present`, `possibly_present` or `likely_absent` with the method's score and the share of analyzed time it covers. No facet SHALL infer or store a singer's gender, age, identity or any attribute of a person.

#### Scenario: Instrumental input
- **WHEN** an instrumental recording from the facet evaluation set is analyzed
- **THEN** the result is not `likely_present`, and it carries a score

#### Scenario: No identity fields
- **WHEN** any facet result is read
- **THEN** it contains no gender, age or speaker-identity field

### Requirement: Structure is reported as candidate boundaries
Structure results SHALL contain only timestamped `candidate_boundary` points and `high_intensity_segment` spans with the method's score. They SHALL NOT use the labels drop, build, breakdown or chorus unless a later change adds an evaluated classifier for that label.

#### Scenario: Boundary in a test signal
- **WHEN** a recording that switches from quiet noise to loud noise at 62 seconds is analyzed
- **THEN** a `candidate_boundary` is reported within 3 seconds of 62 seconds, and no result uses the label drop

### Requirement: Analyzed coverage is recorded and reported
Each facet result SHALL record the span of audio it analyzed. When a method caps its input, the result SHALL report the cap and the asset's full duration. A preview asset's result SHALL be marked as describing the preview, not the full track.

#### Scenario: Capped analysis
- **WHEN** a method with a 600-second cap analyzes a 900-second asset
- **THEN** the result records span 0 to 600 seconds, duration 900 seconds and capped true

#### Scenario: Preview only
- **WHEN** facets are read for a track whose only linked asset is a 30-second preview
- **THEN** every result is marked kind `preview` with a 30-second analyzed span

### Requirement: Facet jobs are operator-started and resilient
Facet jobs SHALL be queued only by the operator's facet command, on the queue each method declares (`gpu` for neural methods, the default CPU queue otherwise), for assets with a file and no current result. No schedule, API route or bot command SHALL queue them. A missing, pruned or undecodable asset SHALL be recorded as `failed` with a reason, and the batch SHALL continue.

#### Scenario: Backfill
- **WHEN** 5 assets have files, 2 already have current tempo results, and the operator runs the facet command for tempo
- **THEN** jobs covering exactly the other 3 assets are queued and the command prints their IDs

#### Scenario: Pruned file in a batch
- **WHEN** a facet job processes 3 assets and one file has been pruned
- **THEN** the job finishes, 2 results are `available`, and the third is `failed` with reason `file_deleted`

#### Scenario: Nothing schedules facets
- **WHEN** the worker's registered schedules are listed
- **THEN** none queues a facet job

### Requirement: Facet results are revision-aware and follow their asset
A result made by an older method version or pipeline SHALL be counted as missing and replaced when the asset is processed again. Results SHALL remain when an asset's file is pruned and SHALL be deleted with the asset row.

#### Scenario: Method version bumped
- **WHEN** the enabled tempo method's version changes and the operator runs the facet command
- **THEN** assets with older tempo results are queued, and processing replaces each row with one at the new version

#### Scenario: Asset deleted
- **WHEN** an asset row with facet results is deleted
- **THEN** none of its facet rows remain

### Requirement: Percentiles are relative to the requesting user's eligible library
A facet percentile SHALL be computed at read time against the requesting user's eligible library: distinct assets that `audio_for_track` returns with status `ok` for tracks in that user's included plays, with an `available` result for the same facet and method version. It SHALL report the reference count. With fewer than 30 reference assets it SHALL be `insufficient_sample`. No percentile SHALL be stored on a shared asset.

#### Scenario: Percentile with its reference
- **WHEN** a user's eligible library has 400 assets with brightness results and the track's centroid exceeds 328 of them
- **THEN** the brightness percentile is 82 with reference count 400

#### Scenario: Small library
- **WHEN** a user's eligible library has 29 assets with brightness results
- **THEN** the percentile is `insufficient_sample` with the actual count, and no number is returned

#### Scenario: Another user's library is not used
- **WHEN** user A requests a percentile for a track that user B has played but A has not
- **THEN** the reference set contains only assets for tracks A has played
