# Design

## Context

See proposal.md. Evidence: docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md section 2 (tools
table: Demucs unmaintained, Whisper is speech recognition, measure word error and
hallucinations, check rights to retain or display lyrics; "Longer-form descriptions and
lyrics: exploratory leads": MusiLingo uses a 7B Vicuna, LLark is a published approach,
Audio Flamingo 3 is non-commercial research only, Qwen2.5-Omni-3B has a research license,
LyricWhiz uses ChatGPT post-processing, the pitch-correction paper does not establish
accuracy here; `trust_remote_code` review) and section 3 (datasets: Jam-ALT, Song
Describer, MuChoMusic and their terms). docs/research/MUSIC-ANALYSIS.md idea 8: lyric
themes are an optional later experiment, not a guaranteed Whisper capability.

Constraints: GTX 1070, 8 GB, Pascal sm_61, shared with production `gpu` jobs; ADR 0004 keeps
model dependencies in audio-lab's own lock; Pascal has no tensor cores and limited fp16
throughput, and bitsandbytes or FlashAttention support on sm_61 is unverified.

## Goals / Non-Goals

**Goals:**
- Numbers (accuracy, hallucination, VRAM, latency) that a later proposal can cite.
- A license and code-review record for each lead.
- Zero risk of private audio, transcripts or lyrics leaving the machine or reaching users.

**Non-Goals:**
- Choosing a production model, or any production integration.
- A lyric or caption dataset of the owner's tracks.

## Decisions

### Decision 1: A separate optional extra in audio-lab

Add a `lyrics-caption` extra to `services/audio-lab/pyproject.toml` (Whisper via
`openai-whisper` or `transformers`, Demucs, and per-model packages), resolved against the
existing Pascal torch pin. Models whose dependencies conflict with that pin are recorded as
`unavailable` rather than forcing a second torch.

Alternative: a separate project per model. Rejected for now; revisit only if conflicts
make the extra unresolvable.

### Decision 2: Local-only enforcement in code

The commands accept no endpoint or API-key settings, refuse environment variables such as
`OPENAI_API_KEY`/`OPENAI_BASE_URL` when present, and set `HF_HUB_OFFLINE=1` after an
explicit `download` step that fetches pinned weights and public datasets. Tests block
sockets during inference.

Alternative: trusting configuration. Rejected: the cost of one leaked private transcript
outweighs the convenience.

### Decision 3: Evaluation sets and metrics

- Lyrics: Jam-ALT with its normalization (WER, CER, per language). Hallucination counts
  words emitted inside gaps of at least 5 s between timed lines, using Jam-ALT's line
  timing; Jam-ALT is not word-aligned, so timing accuracy is not scored. Configurations:
  Whisper sizes that fit (tiny to large), with and without Demucs `htdemucs` vocals.
- Captions: Song Describer subset (captions as references; metrics reported with n and as
  weak evidence) and MuChoMusic accuracy for items with obtainable audio.
- Pitch correction: the paper's method if code and weights are available under a usable
  license; otherwise recorded `unavailable`. Agreement is reported only against labels
  that exist.
- Owner tracks: an optional private inspection mode producing transcripts and captions in
  the out-of-repo run directory for the owner to read; no scores, nothing aggregated into
  docs beyond counts.

### Decision 4: Precision ladder per model

Each model is tried in fp32, then fp16, then 8-bit or 4-bit where its library supports
Pascal, stopping at the first that loads and completes a smoke clip; every attempt and its
error is recorded. This keeps "does not fit" as data instead of a silent skip.

## Risks / Trade-offs

- [Benchmarks unlike the owner's library] -> results labelled exploratory; private
  inspection lets the owner judge fit without publishing anything.
- [Heavy runs block production `gpu` jobs] -> run when the worker is idle, record the
  timing; the operator can stop the run.
- [Lyrics licensing] -> lyrics and transcripts never stored in the repo or shown; docs carry
  aggregates only.
- [Remote code in model repos] -> pinned, reviewed revisions only.
- [Dependency rot (Demucs unmaintained)] -> pinned versions; a broken install is recorded,
  not patched around.

## Migration Plan

None: audio-lab only, no production deploy. Removal is deleting the commands and extra.

## Open Questions

- Which Whisper size and precision the owner considers worth a production proposal, given
  rack time.
- Whether any captioning model fits the 1070 at usable quality, or whether this direction
  waits for different hardware (which would need its own ADR).
- Whether the pitch-correction method's code and weights are obtainable under usable terms.
