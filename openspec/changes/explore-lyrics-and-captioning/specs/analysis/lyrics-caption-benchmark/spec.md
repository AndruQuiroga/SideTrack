# Spec Delta

## Purpose

Measure, inside audio-lab only, how well local lyric-transcription, audio-captioning and pitch-correction models work on public benchmarks and on the rack GPU, with license records and local-only inference, before any production feature is proposed. Nothing in this capability reaches users.

## ADDED Requirements

### Requirement: Inference is local only
`audio-lab lyrics`, `audio-lab captions` and the pitch-correction run SHALL run every model on the local machine and SHALL refuse any configured remote endpoint or API key for inference. Private audio, transcripts and captions SHALL NOT be sent to any remote service; network access SHALL be limited to downloading pinned model weights and public datasets.

#### Scenario: Remote endpoint refused
- **WHEN** the operator configures an OpenAI-compatible remote endpoint for post-processing
- **THEN** the command exits with an error naming the local-only rule and processes nothing

#### Scenario: Inference makes no requests
- **WHEN** a lyrics run executes with models and data already cached and network access blocked
- **THEN** the run completes and no outbound connection is attempted

### Requirement: Candidate models declare license and code records
Each candidate model SHALL declare the licenses of its code, weights and training data, its pinned revision, and whether it loads repository-supplied code. A model that loads repository-supplied code SHALL run only at a pinned revision recorded as reviewed. A model whose license forbids the intended use SHALL be marked not eligible for production in every report.

#### Scenario: Unreviewed remote code
- **WHEN** a model requires `trust_remote_code` and its pinned revision has no review record
- **THEN** the run refuses to load it and records it as `unavailable` with reason "remote code not reviewed"

#### Scenario: Non-commercial weights
- **WHEN** a report includes Audio Flamingo 3
- **THEN** its results are marked non-commercial research only and not eligible for production

### Requirement: Lyric runs report error and hallucination
A lyrics run SHALL report WER and CER on Jam-ALT using its published normalization, per language with n, for each model size with and without Demucs vocal separation, and the amount of text produced on sections annotated as instrumental or silent. It SHALL state that Jam-ALT is not word-aligned and is a 79-song set.

#### Scenario: Per-language results
- **WHEN** a lyrics run covers all Jam-ALT languages
- **THEN** the report lists WER and CER per language and configuration with the number of songs in each

#### Scenario: Hallucination on instrumental sections
- **WHEN** a model emits words during a section with no annotated lyrics
- **THEN** the report counts those words as hallucinated for that configuration

### Requirement: Caption runs use rights-checked public sets
A caption run SHALL evaluate on the Song Describer subset and MuChoMusic questions whose audio is available without YouTube, reporting MuChoMusic accuracy and caption metrics with n. It SHALL NOT use MusicCaps audio or yt-dlp, and SHALL state that a benchmark score does not guarantee correct free-text descriptions.

#### Scenario: YouTube-only items skipped
- **WHEN** a MuChoMusic question's audio is only available from YouTube
- **THEN** the run skips it and reports the skipped count

#### Scenario: Accuracy with n
- **WHEN** a caption run finishes
- **THEN** each model's MuChoMusic accuracy is reported with the number of questions answered and the number that failed

### Requirement: Runs record rack cost and failures
Every run SHALL record per model the precision used, load time, run time per audio minute, peak VRAM and GPU name. A model that runs out of memory, needs an unsupported precision on the GPU or fails to load SHALL be recorded as `unavailable` with the error and SHALL have no quality scores.

#### Scenario: Model too large
- **WHEN** a 7B audio-language model in fp32 exceeds the GTX 1070's memory
- **THEN** the run records it as `unavailable` with the out-of-memory error and reports no accuracy for it

#### Scenario: Cost recorded
- **WHEN** Whisper small transcribes Jam-ALT on the GTX 1070
- **THEN** the report shows precision, load time, seconds per audio minute and peak VRAM

### Requirement: Pitch-correction output is tentative
A pitch-correction run SHALL report its predictions as tentative production-technique estimates with agreement against available labels and n, and SHALL NOT describe any prediction as evidence about an artist's ability or authenticity.

#### Scenario: Report wording
- **WHEN** a pitch-correction report is generated
- **THEN** it labels predictions "possible pitch correction (tentative)" and contains none of fake, authentic or cannot sing

### Requirement: Outputs stay out of the repository and out of production
Run outputs, including transcripts and captions of owner tracks and any lyrics, SHALL be written only outside the repository; the commands SHALL refuse an output path inside it. Docs SHALL record aggregate metrics only. No production package, table, job or route SHALL read these outputs.

#### Scenario: Output inside repository
- **WHEN** the operator passes an output path inside the repository
- **THEN** the command exits with an error and writes nothing

#### Scenario: No production consumer
- **WHEN** the import-linter contracts run
- **THEN** no module under `sidetrack/` or `services/api` imports audio-lab lyric or caption code
