# Spec Delta

## ADDED Requirements

### Requirement: Labelled metrics use optional label files
`audio-lab report` SHALL accept an optional `labels.csv` (seed artist, title, label) and an optional `colisten.csv`. It SHALL match them to manifest assets by normalised artist and title. Without these files, the report SHALL omit the labelled metrics rather than show zeros.

#### Scenario: No label files
- **WHEN** `audio-lab report` runs without `--labels` or `--colisten`
- **THEN** `metrics.json` has no genre, co-listening or sleep figures, and the report says they need label files

### Requirement: Genre precision is measured on the control set
For seeds labelled `genre:<name>`, `audio-lab report` SHALL compute each model's genre precision@10. This is the mean share of a control seed's top-10 neighbours, among control-set tracks only, that carry the same genre label.

#### Scenario: Perfect genre separation
- **WHEN** every control seed's ten nearest control tracks share its genre
- **THEN** that model's genre precision@10 is 1.0

### Requirement: Co-listening hit rate is measured
For each pair in `colisten.csv` where both tracks are in the run, `audio-lab report` SHALL compute each model's co-listening hit rate. This is the share of pair directions (A→B and B→A) in which the partner appears in the track's top 10.

#### Scenario: One direction found
- **WHEN** one co-listened pair has B in A's top 10, but A is not in B's top 10
- **THEN** the hit rate over that pair is 0.5

### Requirement: Sleep-cluster purity is measured
For seeds labelled `sleep`, `audio-lab report` SHALL compute each model's sleep purity: the mean share of a sleep seed's top-10 neighbours that are also labelled `sleep`. It SHALL be reported next to the base rate, which is the share of `sleep` seeds in the pool.

#### Scenario: Purity against base rate
- **WHEN** 10% of seeds are sleep tracks and a model's sleep seeds have 6 of 10 neighbours labelled sleep
- **THEN** that model's sleep purity is 0.6 with a base rate of 0.1

### Requirement: Embedding can skip over-long assets
`audio-lab embed --max-duration SECONDS` SHALL skip any asset whose manifest duration exceeds the limit. Each skipped asset SHALL be recorded as failed with reason `too_long`, and no rows SHALL be written for it.

#### Scenario: Podcast that slipped through
- **WHEN** a manifest asset lasts 3,344 s and `--max-duration 600` is given
- **THEN** it has no embedding rows and appears in `failures.csv` with reason `too_long`

### Requirement: Duels can be limited to chosen models
`audio-lab report --duel-model NAME`, repeatable, SHALL generate duels only between the named models. It SHALL reject a name that the run didn't embed. Neighbour lists and metrics SHALL still cover every model.

#### Scenario: Two finalists
- **WHEN** the report runs with `--duel-model muq --duel-model muq-mulan` on a four-model run
- **THEN** every duel compares MuQ with MuQ-MuLan, and the browse view and metrics still list all four models

#### Scenario: Unknown model
- **WHEN** `--duel-model openl3` is passed
- **THEN** the command exits non-zero, naming `openl3`
