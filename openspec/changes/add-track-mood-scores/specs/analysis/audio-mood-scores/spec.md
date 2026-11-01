# Spec Delta

## Purpose

Stores gated mood probes trained outside production and applies them to stored audio embeddings, so embedded assets have perceived valence and arousal with provenance and user-relative percentiles.

## ADDED Requirements

### Requirement: Probes are stored with provenance
A stored probe SHALL record:
- its embedding model, checkpoint revision and pipeline;
- its training dataset;
- per-dimension evaluation metrics, and whether the splits were artist-grouped;
- the predicted valence–arousal correlation on the scored library;
- its standardisation parameters and weights.

A probe whose model, revision or pipeline differs from the current embeddings SHALL be refused.

#### Scenario: Loading a matching probe
- **WHEN** the operator loads a probe exported for MuQ-MuLan's current revision and pipeline
- **THEN** the probe is stored inactive with its dataset name, metrics and grouping flag

#### Scenario: Mismatched revision
- **WHEN** the operator loads a probe trained on an older revision
- **THEN** the command exits non-zero naming the mismatch and stores nothing

### Requirement: Activation requires a recorded owner gate
A probe SHALL become active only after an evaluation record and an owner listening-check decision of `accepted` are stored for it. The record SHALL cover out-of-domain tracks from the owner's library. Benchmark metrics alone SHALL NOT activate a probe.

#### Scenario: No gate decision
- **WHEN** the operator activates a probe with no stored owner decision
- **THEN** the command exits non-zero with `gate_pending` and no scores are readable for it

#### Scenario: Rejected probe
- **WHEN** the owner decision is `rejected`
- **THEN** activation is refused and the decision and notes remain stored

### Requirement: Embedded assets get raw scores
Scoring SHALL write one raw valence value and one raw arousal value per asset with a current embedding, tagged with the probe version. Assets without a current embedding SHALL be reported, not scored. No score SHALL be estimated for them.

#### Scenario: Scoring the library
- **WHEN** 10 assets have current embeddings and 2 do not
- **THEN** 10 score rows exist with the probe version and the result lists 2 assets as `no_embedding`

### Requirement: Percentiles are relative to the requesting user's eligible library
Percentiles SHALL be computed when read, against the assets linked to the requesting user's eligible plays for the active probe. They SHALL NOT be stored as a global per-asset value. Each response SHALL include the reference population size, probe version and coverage. Below 30 scored eligible assets, percentiles SHALL be `insufficient_sample`.

#### Scenario: Percentile for one user
- **WHEN** an asset's valence is the lowest of a user's 100 scored eligible assets
- **THEN** that user's read returns valence percentile 0 with reference n 100

#### Scenario: Same asset, different users
- **WHEN** two users with different libraries read the same asset
- **THEN** each read returns a percentile and reference n computed from that user's own library

#### Scenario: Small library
- **WHEN** a user has 12 scored eligible assets
- **THEN** percentiles are `insufficient_sample` while raw scores are still returned

### Requirement: Superseded probes are never mixed
After a new probe version is activated, reads SHALL return only scores of the active version. Scores of other versions SHALL NOT be mixed into results.

#### Scenario: New probe
- **WHEN** a second probe version is activated before rescoring
- **THEN** mood reads report `not_scored` for assets lacking active-version scores
