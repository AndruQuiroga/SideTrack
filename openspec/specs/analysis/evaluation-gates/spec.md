# analysis/evaluation-gates Specification

## Purpose
Defines the evidence an audio-analysis claim needs before any user sees it: a frozen
evaluation record, task-specific metrics, coverage, failure and robustness reports, the
owner's recorded decision, and a register of evaluation datasets and their rights.

## Requirements

### Requirement: User-facing analysis claims require an approved gate
Each analysis claim shown to a user SHALL have an entry in the evaluation register with a status of `approved`, `gate_pending`, `incomplete`, `rejected` or `stale`. Only `approved` permits the claim to be user-facing. The repo check SHALL fail when a capability linked to a gate entry is marked `works` in `docs/status.yaml` while that entry is not `approved`.

#### Scenario: Pending gate blocks a works status
- **WHEN** the register lists claim `mood-estimate` as `gate_pending` with status capability "Track mood scores", and `docs/status.yaml` marks "Track mood scores" as `works`
- **THEN** `python scripts/check_evaluations.py` exits non-zero naming `mood-estimate` and its status

#### Scenario: Approved gate allows a works status
- **WHEN** the register lists claim `mood-estimate` as `approved` with complete evidence and `docs/status.yaml` marks its capability `works`
- **THEN** the check reports no error for that claim

### Requirement: An approval is bound to exact revisions
A gate entry SHALL name the model, checkpoint revision, probe or head revision, pipeline version and label-vocabulary version it evaluated. When any of them differs from what the feature declares, the entry SHALL be reported `stale` and SHALL NOT count as approved.

#### Scenario: Pipeline version changed
- **WHEN** an approved entry names pipeline `w10-t3-cap180-fp32-mean-l2-v1` and the feature declares `w10-t3-cap180-fp32-mean-l2-v2`
- **THEN** the check reports the entry `stale`, naming both pipeline versions

### Requirement: Evaluation records freeze the task and population
An evaluation record SHALL state the task, the claim's wording, the model and checkpoint revisions, preprocessing, preview or full source, analyzed duration, time range, label vocabulary and version, population counts, and the evaluation date. `audio-lab gate check` SHALL report a record missing any of these as `incomplete`, naming each missing field.

#### Scenario: Missing checkpoint revision
- **WHEN** `audio-lab gate check` reads a record without a checkpoint revision
- **THEN** it reports `incomplete`, names `checkpoint_revision`, and exits non-zero

#### Scenario: Complete record
- **WHEN** a record contains every required field and the task-specific evidence for its task
- **THEN** `audio-lab gate check` reports `complete` and exits zero

### Requirement: Records include a held-out challenge set
A record SHALL report how many evaluated items are obscure tracks, electronic styles and altered versions (sped-up, slowed, edits or covers), each held out from any fitting. A category with no items SHALL be reported `not_covered`, and the record's summary SHALL show that the claim is unevaluated for that category.

#### Scenario: No altered versions
- **WHEN** a record has 40 obscure and 60 electronic held-out items but no altered versions
- **THEN** the summary lists altered versions as `not_covered`

### Requirement: Splits avoid leakage and disclose grouping
When a record fits anything (a probe, head or threshold), it SHALL state whether splits were grouped by artist, by recording, or not grouped, with the reason. It SHALL report items whose recording, alternate upload or audio hash appears on both sides of a split; any such item SHALL make the record `incomplete` until removed or accepted by the owner with a reason.

#### Scenario: Ungrouped dataset
- **WHEN** a record states `grouping: none` with reason `artist metadata unavailable`
- **THEN** the gate summary shows "not artist-grouped: scores may be optimistic" next to every fitted metric

#### Scenario: Same audio in train and test
- **WHEN** two items with the same audio SHA-256 fall in different folds
- **THEN** `audio-lab gate check` reports `incomplete` and lists the duplicated hash

### Requirement: Neighbour claims use blind pairwise judgments
A record for a neighbour or discovery claim SHALL include blind pairwise listener judgments and a precision or ranking measure, compared with a random control and a simple recent-or-frequent baseline. It SHALL report "same recording" separately from "sounds similar" and SHALL NOT count a version or duplicate of the seed as a correct neighbour.

#### Scenario: Missing baseline
- **WHEN** a neighbour record has listener judgments but no random-control result
- **THEN** `audio-lab gate check` reports `incomplete` naming `random_control`

#### Scenario: Duplicate counted separately
- **WHEN** a judged neighbour is the seed's own preview
- **THEN** it is counted under "same recording" and excluded from the sounds-similar precision

### Requirement: Text-label claims test prompt sensitivity
A record for a text label or text search claim SHALL include several prompt variants per term, hard negatives and close confusions, an abstention option, and a comparison of raw cosine with any library-relative ranking. It SHALL NOT present a cosine or z-score as a probability or calibrated confidence.

#### Scenario: Single prompt per term
- **WHEN** a text-label record evaluates each term with one prompt
- **THEN** `audio-lab gate check` reports `incomplete` naming `prompt_variants`

#### Scenario: Similarity labelled as confidence
- **WHEN** a record's claim wording calls a cosine score a "confidence" or "probability"
- **THEN** the check reports `incomplete` naming `uncalibrated_confidence`

### Requirement: Mood claims evaluate both axes against baselines
A record for a mood claim SHALL report each axis separately against a mean-only baseline, a relative-ranking measure, calibration of any displayed range, and the correlation between predicted axes on the target library next to the human-rating correlation. Splits SHALL be artist-grouped when metadata permits; otherwise the grouping disclosure applies.

#### Scenario: Correlated axes disclosed
- **WHEN** predicted valence and arousal correlate at 0.92 on the owner's library and human ratings at 0.57
- **THEN** the gate summary shows both correlations and a warning that the axes may not be distinguished

#### Scenario: One axis only
- **WHEN** a mood record reports valence but not arousal
- **THEN** `audio-lab gate check` reports `incomplete` naming `arousal`

### Requirement: Timing claims use tolerance windows
A record for beats, downbeats, tempo or section boundaries SHALL declare its timestamp tolerance before scoring, report boundary accuracy and label accuracy separately, and report half- and double-tempo agreement for tempo. Named section classes absent from the reference annotations SHALL NOT be claimed.

#### Scenario: Tolerance missing
- **WHEN** a section-boundary record has accuracy figures but no declared tolerance
- **THEN** `audio-lab gate check` reports `incomplete` naming `tolerance_s`

#### Scenario: Drop label without annotations
- **WHEN** a record's claim wording includes "drop" and its reference annotations have no drop class
- **THEN** the check reports `incomplete` naming `unsupported_label`

### Requirement: Records report coverage and failures with exact counts
A record SHALL report exact counts of evaluated items, missing audio, ambiguous links, short files, model failures, unknown or abstained categories, rater disagreement and items excluded with reasons, and the excluded fraction. It SHALL NOT fill missing values, interpolate missing periods or derive a confidence solely from similarity scores.

#### Scenario: Failures counted
- **WHEN** 5 of 200 items fail to decode and 12 are shorter than 3 s
- **THEN** the record reports `model_failures: 5`, `short_files: 12` and an excluded fraction computed from those counts

### Requirement: Records test robustness
A record SHALL compare preview with full audio where both exist, loudness-normalized with original audio where relevant, and results across genre and artist groups, clustering seeds and vocabulary versions where they apply. It SHALL declare before scoring what change counts as material, and report uncertainty for the stated sampling unit (track or artist, not repeated plays).

#### Scenario: Material change reported
- **WHEN** a record declares a material change of 0.1 in precision and preview results differ from full results by 0.15
- **THEN** the gate summary flags preview robustness as failed

#### Scenario: Wrong sampling unit
- **WHEN** a record's interval resamples individual plays of the same recordings
- **THEN** `audio-lab gate check` reports `incomplete` naming `sampling_unit`

### Requirement: The owner's decision is required and recorded
Every gate SHALL include representative examples the owner reviewed and the owner's recorded decision: `approve`, `reject` or `correct`, with the date and any corrections or notes. Dataset metrics SHALL NOT substitute for this decision. Without a decision the entry SHALL be `gate_pending`; `reject` SHALL make it `rejected`; `correct` SHALL keep it `gate_pending` until a later `approve`.

#### Scenario: Dataset scores without owner review
- **WHEN** a mood record has DEAM R² figures and no owner decision
- **THEN** the register check reports the entry `gate_pending`, not `approved`

#### Scenario: Owner rejects
- **WHEN** the owner records `reject` with a note
- **THEN** the entry becomes `rejected` and the note is kept in the record

#### Scenario: Owner corrects
- **WHEN** the owner records `correct` with three relabelled examples
- **THEN** the entry stays `gate_pending` and the corrections are kept in the record

### Requirement: Evaluation datasets have a rights register
Every dataset an evaluation record cites SHALL appear in `docs/evaluations/datasets.yaml` with its source, intended use, recorded terms for audio and for annotations, known gaps, acquisition method, storage location and review date. A record citing a dataset that is missing, or whose entry is `rights_unconfirmed` for that use, SHALL NOT be approved.

#### Scenario: Unregistered dataset
- **WHEN** a record cites `pmemo` and the rights register has no `pmemo` entry
- **THEN** the register check reports the record `incomplete` naming `pmemo`

#### Scenario: Rights unconfirmed
- **WHEN** the register marks MusAV's previews `rights_unconfirmed` and an approved entry cites MusAV audio
- **THEN** the check exits non-zero naming MusAV and the claim

### Requirement: Dataset audio is never acquired automatically
Evaluation tooling SHALL NOT invoke yt-dlp, download from YouTube or schedule any acquisition. Datasets whose audio exists only as YouTube references SHALL be registered as annotation-only unless the owner manually holds the audio, and the register SHALL say which.

#### Scenario: YouTube-referenced dataset
- **WHEN** an evaluation preparation command is given MusicCaps metadata without local audio
- **THEN** it prepares no audio, reports the items as `no_local_audio`, and starts no download

### Requirement: Personal and dataset data stay out of the repo
Evaluation records with per-track results, dataset audio and dataset annotations SHALL be written outside the repository working tree. Only aggregate gate summaries and the two registers SHALL be committed. `audio-lab gate` SHALL refuse an output path inside the working tree.

#### Scenario: Output inside the repo
- **WHEN** `audio-lab gate check --out` points inside the git working tree
- **THEN** the command exits non-zero and writes nothing

#### Scenario: Summary safe to commit
- **WHEN** `audio-lab gate summarize` writes a summary for the register
- **THEN** the summary contains aggregate figures and counts and no artist, title, file path or per-track value
