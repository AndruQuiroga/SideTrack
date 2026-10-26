# Spec Delta

## Purpose

Defines the audio lab benchmark that decides whether any audio model is good enough for Sidetrack: what it runs, what it records, how it compares models fairly, and how the owner's judgement is captured.

## ADDED Requirements

### Requirement: Runs embed manifest assets with declared models
`audio-lab embed` SHALL read an audio manifest, run each requested model adapter on every listed asset, and write one embedding row per asset per model to `embeddings.parquet` in a new run directory. Each row SHALL carry the run ID, model name, asset SHA-256, kind, embedding vector and its dimension.

#### Scenario: Embedding a small manifest
- **WHEN** `audio-lab embed` runs one model over a manifest of 3 assets
- **THEN** the run directory's `embeddings.parquet` has 3 rows for that model, each with a vector of the adapter's declared dimension

#### Scenario: Asset file missing
- **WHEN** a manifest row's file doesn't exist
- **THEN** that asset is recorded as failed with reason `missing_file` in the run's results, and the other assets are still embedded

### Requirement: Runs are versioned and reproducible
Every run SHALL write `run.json` with:
- the run ID and start time
- the git commit
- each adapter's checkpoint, revision, licence, sample rate, embedding dimension, pooling and dtype
- the GPU name, driver, CUDA and torch versions
- the SHA-256 of the manifest

A run MUST NOT overwrite an existing run directory.

#### Scenario: Two runs
- **WHEN** `audio-lab embed` runs twice with the same output root
- **THEN** there are two run directories with different IDs, each with its own `run.json` and `embeddings.parquet`

### Requirement: Runs record performance
For each model, a run SHALL record:
- total audio seconds processed
- wall-clock seconds
- throughput in audio seconds per second
- peak GPU memory in MiB
- the number of failed assets

These are measured on the hardware that ran it.

#### Scenario: Performance recorded
- **WHEN** a run completes on a GPU
- **THEN** `run.json` contains those five figures for each model, and the peak GPU memory is greater than zero

### Requirement: Unavailable models are reported, never faked
An adapter whose weights, libraries or device can't be loaded SHALL report the model as unavailable with its reason. It SHALL produce no embedding rows. No code path MAY return constant, random or placeholder embeddings.

#### Scenario: Model libraries not installed
- **WHEN** `audio-lab embed --model muq` runs without the `models` extra installed
- **THEN** the command reports `muq` unavailable with a message naming the missing package, and writes no rows for it

### Requirement: Neighbours are computed within one model
`audio-lab report` SHALL rank neighbours by cosine similarity between embeddings of the same model and run only. It SHALL exclude a seed's own assets from its neighbour list. It MUST NOT compare or combine embeddings from different models.

#### Scenario: Own preview excluded
- **WHEN** a seed has both a full track and a preview
- **THEN** neither of them appears in that seed's neighbour list

#### Scenario: Separate models
- **WHEN** a run contains MuQ and CLAP embeddings
- **THEN** each model's neighbour lists contain only assets embedded by that model, and no similarity is computed between a MuQ and a CLAP vector

### Requirement: Self-retrieval is measured
For seeds with both a full asset and a preview asset, the report SHALL give each model's rate of ranking the seed's own full track first among full tracks for its preview (recall@1), and within the first ten (recall@10).

#### Scenario: Perfect retrieval
- **WHEN** every preview's nearest full-track embedding belongs to its own seed
- **THEN** that model's recall@1 is 1.0

### Requirement: The report captures the owner's judgement
`audio-lab report` SHALL write a self-contained static HTML file. For each seed, it shows the top 10 neighbours per model with artist and title, local playback of the owner's audio files, and good, bad and unsure controls per seed and model. The owner's choices SHALL survive a reload and be exportable as `verdicts.json`. The report MUST NOT load scripts or styles from the network.

#### Scenario: Recording verdicts
- **WHEN** the owner marks MuQ "good" for 2 seeds and "bad" for 1, reloads the page, and exports
- **THEN** `verdicts.json` contains those 3 verdicts tagged with the run ID

### Requirement: Scoring summarises agreement per model
`audio-lab score` SHALL read `verdicts.json` for a run and report, per model, the counts of good, bad and unsure verdicts and the agreement rate good ÷ (good + bad). It SHALL refuse verdicts whose run ID doesn't match the run.

#### Scenario: Scoring
- **WHEN** verdicts give MuQ 8 good, 2 bad and 1 unsure
- **THEN** the score for MuQ is 8 good, 2 bad, 1 unsure, agreement 0.80

#### Scenario: Wrong run
- **WHEN** `audio-lab score` is given verdicts exported from a different run
- **THEN** it exits non-zero, naming both run IDs
