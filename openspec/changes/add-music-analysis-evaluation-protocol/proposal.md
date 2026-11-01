# Proposal

## Why

Sidetrack is about to turn audio embeddings into claims a person reads about their own
music (mood, themes, neighbours, eras), and the research notes show how easily such claims
outrun their evidence: the mood probe's DEAM scores were not artist-grouped, its two axes
correlate at 0.88 on the owner's library, and only the owner's listening check has passed
(docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md, section 3). The project has a benchmark
for choosing an embedding model, but no rule for when *any* analysis result is good enough
to show a user. This change writes that rule down, with the evaluation-data rights it
depends on, before the analysis proposals are applied.

## What Changes

- **An evaluation gate for every user-facing analysis claim.** A claim (for example
  "mood estimate", "suggested theme", "nearest in your library", "candidate listening
  shift", "tempo") may reach a user only after a recorded evaluation passes for the exact
  model, checkpoint, probe and pipeline revisions it uses.
- **A frozen evaluation record** per claim: task, population, model and checkpoint
  revisions, preprocessing, preview/full source, analyzed duration, time range, label
  vocabulary, coverage, held-out obscure/electronic/altered tracks, and whether splits
  were artist- or recording-grouped (and why not, when they were not).
- **Task-specific evidence**, following section 3 of the notes:
  blind pairwise listener judgments and ranking measures for neighbours (with "same
  recording" kept separate from "sounds similar"); prompt variants and hard negatives for
  text labels; both mood axes, relative rankings, calibration and simple baselines for
  mood; timestamp tolerances with separate boundary and label accuracy for beats and
  sections.
- **Coverage, failure and robustness reports** (missing audio, ambiguous links, short
  files, model failures, exclusions; preview vs full, loudness, genre/artist groups,
  seeds, vocabulary versions), with uncertainty reported for the right sampling unit.
- **The owner's human gate**: examples to listen to and a recorded approve / reject /
  correct decision. Dataset scores never substitute for it.
- **A dataset-rights register** (`docs/evaluations/datasets.yaml`) recording, for DEAM,
  MusAV, MTG-Jamendo, PMEmo, MusicCaps, Song Describer, MuChoMusic, Jam-ALT and Harmonix,
  what each is used for, its recorded terms and gaps, how audio may be obtained (by the
  owner, manually, never by automated or scheduled yt-dlp) and where it is stored.
- **An evaluation register** (`docs/evaluations/register.yaml`) listing each claim's gate
  status, plus an `audio-lab gate` command that checks a record's completeness and a repo
  check that fails CI when a claim is marked approved without its evidence, or when
  `docs/status.yaml` marks a gated capability **works** before its gate is approved.

Out of scope:
- Running any new evaluation, collecting labels, or deciding whether any current model
  passes. The first register entries record the evidence that already exists, honestly
  marked `gate_pending` or `incomplete`.
- Changing the model-selection benchmark (`analysis/audio-benchmark`) or the mood-probe
  work merged from `add-mood-probe-benchmark`; those keep their own specs.
- Production code, routes, pages or database changes. Each analysis feature's own change
  enforces its gate status in the product.
- Downloading, mirroring or committing any dataset audio, annotation file or per-track
  result. Only aggregate figures enter the repo.
- Legal advice. The rights register records what the sources say and what is unknown; it
  does not certify permission.

## Capabilities

### New Capabilities
- `analysis/evaluation-gates`: what evidence an analysis claim needs before it becomes
  user-facing, how that evidence is recorded and checked, the owner's decision, and the
  register of evaluation datasets and their rights.

### Modified Capabilities
None. `analysis/audio-benchmark` stays the model-selection benchmark; this capability
governs product claims built on whichever model it selects.

## Impact

Current state:
- **Observed:** `services/audio-lab/src/audio_lab/cli.py` offers `embed`, `report`, `seeds`,
  `control-seeds`, `parity` and `score`; nothing records a per-claim evaluation or an
  owner decision beyond blind duel votes (`duels.py`, `score.py`).
- **Observed:** `add-mood-probe-benchmark` added `mood-probe` and emotion-dataset
  preparation (`services/audio-lab/src/audio_lab/mood.py`, `emotion.py`) and modifies
  `analysis/audio-benchmark` in its own change `add-mood-probe-benchmark`. Run
  `20261031-204732-9b07ff0` reports DEAM valence R² 0.615 and arousal R² 0.688, not
  artist-grouped, and the owner passed the listening check on 2026-10-31 (`docs/AUDIO-BENCHMARK.md`).
- **Observed:** production holds 862 MuQ-MuLan 512-d vectors, one mean-pooled vector per
  asset over at most the first 180 s (`sidetrack/analysis/embeddings/registry.py`,
  `PIPELINE = "w10-t3-cap180-fp32-mean-l2-v1"`); no HTTP route uses them (docs/STATUS.md,
  "Audio embeddings").
- **Observed:** `analysis/benchmark-seeds` already forbids writing personal benchmark
  outputs inside the repo.
- **Observed:** `docs/evaluations/` does not exist; no dataset-rights record exists apart
  from the research notes' table.
- **Assumed:** each listed dataset's terms are as recorded in the research notes on
  2026-10-31; the register marks every entry for re-checking at the exact revision used.

Affected:
- `services/audio-lab/` (new `gate` command, record schema, tests with synthetic records).
- `scripts/check_evaluations.py` and CI (register and status cross-check).
- Docs: new `docs/evaluations/` (README, `register.yaml`, `datasets.yaml`),
  `docs/AUDIO-BENCHMARK.md` (link), `docs/research/MUSIC-ANALYSIS.md` (link),
  `docs/status.yaml`.
- Dependents: `add-track-mood-scores`, `add-sound-themes`, `add-weekly-listening-profile`,
  `add-listening-visuals`, `add-sound-compatibility`, `add-listening-journey` and
  `add-share-consent` cite a gate entry for each claim they show.
