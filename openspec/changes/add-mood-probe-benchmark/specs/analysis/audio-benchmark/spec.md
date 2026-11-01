# Spec Delta

## ADDED Requirements

### Requirement: Emotion datasets become ordinary benchmark inputs
The audio lab SHALL convert a local emotion dataset directory into a manifest that `audio-lab embed` accepts and a mood label file with one row per clip, holding its asset hash, valence, arousal and group. Valence and arousal SHALL be rescaled to the range -1 to 1. Clips without audio or without a rating SHALL be counted and left out, never filled in. Output MUST be refused inside the repo.

#### Scenario: Preparing a dataset
- **WHEN** the operator prepares a dataset of 3 clips with ratings on a 1 to 9 scale
- **THEN** the manifest has 3 rows that `audio-lab embed` reads, and a rating of 5 becomes 0

#### Scenario: Clip without audio
- **WHEN** a rated clip has no audio file
- **THEN** it is left out of both files and counted in the summary

#### Scenario: Output inside the repo
- **WHEN** the output path is inside the repository
- **THEN** the command exits non-zero and writes nothing

### Requirement: Mood probes are measured out of sample
`audio-lab mood-probe` SHALL fit a regularised linear probe per model and per dimension, and report R² only on clips held out from fitting. Regularisation strength and scaling SHALL be chosen using training clips alone. Clips sharing a group MUST never appear on both sides of a split. Results SHALL be repeatable for the same run, labels and seed.

#### Scenario: Signal in the embeddings
- **WHEN** valence is a linear function of synthetic embeddings plus small noise
- **THEN** the reported valence R² is above 0.9

#### Scenario: No signal
- **WHEN** labels are shuffled against the embeddings
- **THEN** the reported R² is at or below 0.05

#### Scenario: Grouped clips
- **WHEN** several clips share a group
- **THEN** every fold keeps all clips of that group on one side

#### Scenario: Same inputs
- **WHEN** the command runs twice with the same inputs and seed
- **THEN** both `mood.json` files have identical scores

### Requirement: Mood results are honest about their limits
`mood.json` SHALL record the run ID, label file hash, clip count, model revision, seed and fold count, with mean and spread of R² per dimension and a mean-only baseline. Labels that match no embedding SHALL be counted. A model missing from the run, or too few matched clips, SHALL be reported as unavailable and MUST NOT produce a score.

#### Scenario: Model not in the run
- **WHEN** the operator asks for a model that the run doesn't contain
- **THEN** the command exits non-zero, naming the model, and writes no score for it

#### Scenario: Too few clips
- **WHEN** fewer clips match than the minimum per fold requires
- **THEN** the model is reported as unavailable with the matched count

### Requirement: Models are compared on the same clips
When a run holds two requested models, the command SHALL compare them on the same held-out clips, and report the difference in mean R² with a 95% bootstrap confidence interval. It SHALL call a model ahead only when the interval excludes zero.

#### Scenario: Clear winner
- **WHEN** one model's embeddings carry the signal and the other's are noise
- **THEN** the interval excludes zero and that model is reported as ahead

#### Scenario: Equal models
- **WHEN** both models receive the same embeddings
- **THEN** the interval includes zero and no model is reported as ahead

### Requirement: Probes can describe another run
The command SHALL be able to apply probes fitted on all labelled clips to a second run, writing per-track predictions to a file outside the repo. Predictions SHALL be matched to the fitted model's revision, and a different revision MUST be refused.

#### Scenario: Predicting the owner's library
- **WHEN** the operator applies probes to a run with the same model and revision
- **THEN** the output has valence and arousal for each asset in that run

#### Scenario: Different revision
- **WHEN** the second run used another revision of the model
- **THEN** the command exits non-zero and writes no predictions
