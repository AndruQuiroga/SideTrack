# analysis/audio-benchmark Specification

## Purpose
Defines the audio lab benchmark that decides whether any audio model is good enough for Sidetrack: what it runs, what it records, how it compares models fairly, and how the owner's judgement is captured.

## Requirements

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

### Requirement: Neighbour lists are described by automatic metrics
`audio-lab report` SHALL compute per model: the same-artist rate (mean share of a seed's same-artist seeds in its top 10), separation (mean gap between best and median neighbour similarity), and per pair of models the overlap (mean share of top-10 neighbours in common). It SHALL write them with self-retrieval to `metrics.json` and show them. They SHALL NOT pass or fail a model by themselves.

#### Scenario: Same artist found
- **WHEN** an artist has two seeds and a model ranks each seed's other track among its top 10
- **THEN** that model's same-artist rate for those seeds is 1.0

#### Scenario: Identical lists
- **WHEN** two models produce the same top-10 neighbours for every seed
- **THEN** their overlap is 1.0

### Requirement: Duels compare rank-matched picks
For each seed and each pair of models, the report SHALL build at most one duel. It compares the two models' neighbours at the first rank where they pick different tracks. When the two lists agree at every rank, that pair has no duel for the seed. The duel order and the side each candidate appears on SHALL be fixed by the run ID, and spread across all model pairs.

#### Scenario: Models pick the same top track
- **WHEN** MuQ and MERT both rank track X first for a seed, and pick Y and Z respectively at rank 2
- **THEN** the MuQ–MERT duel for that seed compares Y with Z

#### Scenario: Same run, same order
- **WHEN** the report is rendered twice for one run
- **THEN** both pages list the same duels in the same order, with the same sides

### Requirement: The owner judges models in blind duels
The report SHALL be a self-contained HTML file whose main view shows one duel at a time: a seed and two candidates. The owner picks the closer candidate or a tie, using the keyboard. The duel view MUST NOT reveal which model picked which candidate. Playback SHALL start partway into each track. Votes SHALL survive a reload and export as `duels.json` with the run ID. A browse view SHALL list neighbours per model. The report MUST NOT load scripts or styles from the network.

#### Scenario: Recording votes
- **WHEN** the owner answers 3 duels, reloads the page and exports
- **THEN** `duels.json` contains those 3 votes, each with the seed, both models and the winner, tagged with the run ID

#### Scenario: Blind duel
- **WHEN** a duel is shown
- **THEN** the page shows the seed and both candidates' artists and titles, and no model name

### Requirement: Scoring summarises duel results per model
`audio-lab score` SHALL read `duels.json` for a run and report:
- per model: wins, losses, ties and win rate (wins plus half of ties, divided by duels)
- per pair of models: each model's wins and the ties

It SHALL write the result to `scores.json` in the run. It SHALL refuse votes whose run ID doesn't match the run, or that name a model the run didn't embed.

#### Scenario: Scoring
- **WHEN** MuQ wins 6 duels, loses 2 and ties 2
- **THEN** MuQ's score is 6 wins, 2 losses, 2 ties, win rate 0.70

#### Scenario: Wrong run
- **WHEN** `audio-lab score` is given votes exported from a different run
- **THEN** it exits non-zero, naming both run IDs
