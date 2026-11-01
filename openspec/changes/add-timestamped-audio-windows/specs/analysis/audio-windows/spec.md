# Spec Delta

## Purpose

Defines how the per-window audio vectors behind each pooled embedding are stored with their
timestamps, coverage and provenance, how long they are kept, and the evaluation gate that
must pass before any section-level similarity claim reaches a user.

## ADDED Requirements

### Requirement: Window vectors are stored with timestamps and provenance
For every asset the embedding job embeds, the system SHALL store each window vector it pooled with the asset, model, checkpoint revision, pipeline version, window index, start and end in seconds, and whether it is the short tail window. Window indexes for one asset, model, revision and pipeline SHALL be unique and contiguous from zero.

#### Scenario: Full track windows
- **WHEN** the GPU worker embeds a 312-second full track with MuQ-MuLan
- **THEN** 18 window rows exist for the asset, indexed 0 to 17, the first spanning 0 to 10 seconds and the last 170 to 180 seconds, each with a 512-dimension vector, the revision and the pipeline

#### Scenario: Track with a short tail
- **WHEN** a 95-second preview-length asset is embedded
- **THEN** 10 window rows exist, the last spanning 90 to 95 seconds and marked as the tail

#### Scenario: Very short file
- **WHEN** a 2-second asset is embedded
- **THEN** one window row exists spanning 0 to 2 seconds

### Requirement: Windows and pooled vector are written together
The window rows and the pooled embedding for an asset, model, revision and pipeline SHALL be written in one transaction. The stored pooled vector SHALL equal the L2-normalized mean of that asset's stored window vectors.

#### Scenario: Pooled vector reproducible
- **WHEN** an asset's stored window vectors are averaged and L2-normalized
- **THEN** the result has cosine similarity of at least 0.99999 with the asset's stored pooled vector

#### Scenario: Failure mid-write
- **WHEN** writing an asset's window rows fails after its pooled vector was prepared
- **THEN** neither the pooled row nor any window rows for that asset and revision are stored, and the job result lists the asset as failed

### Requirement: Window coverage is recorded
For each asset with windows, the system SHALL report the analyzed span, the asset's full duration, and whether the 180-second cap truncated it. Any read of windows SHALL return these values with them.

#### Scenario: Capped full track
- **WHEN** windows are read for a 312-second full track
- **THEN** the result reports analyzed span 0 to 180 seconds, duration 312 seconds and truncated true

#### Scenario: Uncapped preview
- **WHEN** windows are read for a 30-second preview
- **THEN** the result reports analyzed span 0 to 30 seconds and truncated false

### Requirement: Windows follow revision and asset lifetime
When an asset's pooled embedding is replaced for a new revision or pipeline, its old window rows for that model SHALL be deleted in the same transaction. Window rows SHALL remain when the asset's file is pruned and SHALL be deleted with the asset row.

#### Scenario: Revision replaced
- **WHEN** an asset is re-embedded under a new checkpoint revision
- **THEN** only window rows with the new revision exist for that asset and model

#### Scenario: Asset deleted
- **WHEN** an asset row with window vectors is deleted
- **THEN** none of its window rows remain

### Requirement: Window matches are internal and experimental
The window-match operation SHALL compare two assets' windows only within one model, revision and pipeline, and return the requested number of highest cosine-similarity window pairs, each with both windows' timestamps and the similarity. It SHALL report that an asset has no windows rather than return pairs. No HTTP route, page or bot command SHALL expose its output.

#### Scenario: Preview inside its full track
- **WHEN** window matches are requested between a full track and a preview cut from 60 to 90 seconds of it
- **THEN** the top pair's full-track window starts within 10 seconds of 60 seconds, and every pair lists both timestamps and a similarity no higher than the pair before it

#### Scenario: Asset without windows
- **WHEN** window matches are requested for an asset embedded before windows were stored
- **THEN** the operation reports that the asset has no windows and returns no pairs

#### Scenario: Not exposed over HTTP
- **WHEN** the API's route table is listed
- **THEN** no route returns window vectors, window timestamps or window-match results

### Requirement: Section claims wait for an alignment evaluation
An audio-lab alignment evaluation SHALL locate previews inside their full tracks using window matches and report the share located within 10 seconds of the reference offset, with n. It SHALL also report owner judgments of sampled cross-track window pairs. No user-facing section claim SHALL be added until a change cites a recorded evaluation and the owner's decision.

#### Scenario: Evaluation recorded
- **WHEN** `audio-lab align` runs over preview/full pairs with established reference offsets
- **THEN** the report gives the share located within 10 seconds, n, and the pairs whose offsets could not be established, counted separately

#### Scenario: No reference offset
- **WHEN** a preview's reference offset cannot be established
- **THEN** the pair is excluded from the located share and counted under offsets unavailable
