# Spec Delta

## Purpose

Stores mood probes trained outside production and applies them to stored audio embeddings, so every asset has perceived valence and arousal with provenance.

## ADDED Requirements

### Requirement: Probes are stored with provenance
A stored probe SHALL record its embedding model, checkpoint revision, pipeline, training dataset, cross-validated R? per dimension, standardisation parameters and weights. A probe whose model, revision or pipeline differs from the current embeddings SHALL be refused.

#### Scenario: Loading a matching probe
- **WHEN** the operator loads a probe exported for MuQ-MuLan's current revision and pipeline
- **THEN** the probe is stored with its dataset name and R? values

#### Scenario: Mismatched revision
- **WHEN** the operator loads a probe trained on an older revision
- **THEN** the command exits non-zero naming the mismatch and stores nothing

### Requirement: Every embedded asset gets scores
Scoring SHALL write one valence and one arousal value per asset with a current embedding, tagged with the probe version. Assets without a current embedding SHALL be reported, not scored.

#### Scenario: Scoring the library
- **WHEN** 10 assets have current embeddings and 2 do not
- **THEN** 10 score rows exist with the probe version and the result lists 2 assets as `no_embedding`

### Requirement: Scores include library percentiles
Each score SHALL carry its percentile among all scored assets for the same probe version, recomputed whenever the scored set changes.

#### Scenario: Percentile
- **WHEN** an asset's valence is the lowest of 100 scored assets
- **THEN** its valence percentile is 0

### Requirement: Superseded probes mark scores stale
Loading a new probe version SHALL make reads return only scores of the active version; scores of other versions SHALL not be mixed into results.

#### Scenario: New probe
- **WHEN** a second probe version is activated before rescoring
- **THEN** mood reads report `not_scored` for assets lacking active-version scores
