# Proposal

## Why

Two ideas from the music-analysis research keep coming up: lyric themes, and longer
written descriptions of a track ("a slow, reverb-heavy synth track with a spoken vocal").
Both depend on models that have not been measured on this library or this hardware.
Whisper is speech recognition, not reliable sung-lyric transcription; Demucs is no longer
actively maintained; audio-language models range from non-commercial or research-only
licenses to 7B models whose fp32 weights alone exceed the GTX 1070's 8 GB
(docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md, "Longer-form descriptions and lyrics:
exploratory leads"). Before anyone proposes a product feature, the project needs measured
accuracy, hallucination, licensing and rack cost, gathered in audio-lab where nothing
reaches users.

## What Changes

- **`audio-lab lyrics`**: transcribe the Jam-ALT benchmark (and, separately, owner tracks
  for private inspection) with Whisper model sizes that fit the rack, with and without
  Demucs vocal separation. Report WER and CER using Jam-ALT's normalization, per language,
  hallucinated text on instrumental or silent sections, run time, load time and peak VRAM.
- **`audio-lab captions`**: run audio-language candidates (MusiLingo, LLark,
  Audio Flamingo 3, Qwen2.5-Omni-3B) that pass a license and fit check, on the Song
  Describer subset and on MuChoMusic multiple-choice questions, reporting accuracy, caption
  metrics with n, VRAM, latency and failures. Models that do not fit or cannot run locally
  are recorded as `unavailable` with the reason.
- **A tentative pitch-correction detector run**, reporting agreement with whatever labels
  exist; never framed as an authenticity judgment.
- **Local-only inference.** The commands refuse remote endpoints; private audio and
  transcripts never leave the machine. LyricWhiz's ChatGPT post-processing is not
  implemented.
- **Model license records** for every candidate, and a pinned, reviewed revision for any
  model that loads repository-supplied code (`trust_remote_code`).

### Out of scope

- Any production code, database table, worker job, HTTP route or user-facing output.
  Transcripts, captions and pitch-correction predictions are never shown in the bot or web.
- Storing or committing lyrics or owner transcripts in the repository; docs record
  aggregate metrics only.
- MusicCaps or any YouTube-sourced audio, and any use of yt-dlp for evaluation data.
- Fine-tuning or training any model.
- Adding PyTorch, Whisper, Demucs or audio-LLM dependencies to the root lock or the GPU
  worker.

## Capabilities

### New Capabilities

- `analysis/lyrics-caption-benchmark`: audio-lab-only exploratory runs for lyric
  transcription, audio captioning/question answering and pitch-correction detection, with
  local-only inference, license records and rack cost.

### Modified Capabilities

- None. Production capabilities are unchanged.

## Impact

- **Observed:** `services/audio-lab` is the benchmark CLI with its own lock; PyTorch is in
  its `models`/`models-pascal` extras and in `services/gpu-worker`, not in the root
  project (ADR 0004, `services/audio-lab/pyproject.toml`).
- **Observed:** audio-lab's `seeds` command refuses an output path inside the repository
  because its output is personal data (`services/audio-lab`).
- **Observed:** the rack GPU is a GTX 1070 (8 GB, Pascal sm_61) running fp32, shared and
  serial on the `gpu` queue; MuQ-MuLan peaks around 2.8 GB and MuQ around 5.3 GB
  (docs/STATUS.md, run `20261027-172855-0c32766-dirty`; ADR 0010).
- **Observed:** no lyric, caption or transcript data exists anywhere in the schema
  (`sidetrack/analysis/models.py`).
- **Assumed:** Whisper large in fp32 needs about 6 GB plus activations; a 7B language
  model in fp32 needs about 28 GB and Qwen2.5-Omni-3B more than 8 GB, so they need fp16 or
  quantization, whose support on Pascal is unverified. Task 3.1 measures this.
- **Assumed:** Jam-ALT's 79 songs and four languages, and Song Describer's roughly 1,100
  captions for 706 recordings, are too small and too unlike the owner's library to predict
  quality on it; results are reported as exploratory.

### Affected

- `services/audio-lab` (new commands, an optional extra for these models, tests),
  docs/AUDIO-BENCHMARK.md, docs/status.yaml.

## Dependencies

- None. This change is independent of the listening and production analysis changes.
- A later production proposal (lyric themes, captions, a pitch-correction facet in
  `add-track-facet-card`) would depend on this change's recorded results and need its own
  ADR.
