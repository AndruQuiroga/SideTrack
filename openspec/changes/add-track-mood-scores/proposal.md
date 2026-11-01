# Proposal

## Why

The mood probe benchmark (run `20261031-204732-9b07ff0`, branch `feat/mood-probe-benchmark`) showed that a ridge probe on MuQ-MuLan embeddings predicts DEAM valence (R² 0.615) and arousal (R² 0.688), but the probe lives only in audio-lab. Weekly profiles need per-track perceived-mood values in Postgres. These values must be versioned so a retrained probe never mixes with old values. They must also be gated on evidence that they are meaningful for the owner's music, which differs strongly from DEAM.

## What Changes

- A stored, versioned linear probe for valence and arousal on one embedding model, revision and pipeline. It records the weights, standardisation, training dataset, evaluation summary and gate decision.
- An activation gate: a probe cannot become active until its evaluation record and the owner's listening-check decision are stored. DEAM R² alone does not pass the gate.
- Raw per-asset valence and arousal scores computed from stored embeddings on the CPU worker. This is a 512×2 matrix product with no GPU and no torch.
- Percentiles computed **at read time against the requesting user's eligible library**, never stored as one global percentile on a shared asset. Each read returns its reference population (n, probe version, coverage).
- An operator command that loads a probe exported by audio-lab and scores all embedded assets.

Out of scope:
- Presenting mood to users (`add-weekly-listening-profile`, `add-listening-visuals`).
- Retraining in production. Training stays in audio-lab.
- Felt mood or the listener's emotional state. These are estimates of perceived emotion in the music; see notes §2 (GEMS).
- Richer emotion vocabularies (GEMS categories). These need separate labels and evaluation.
- Segment- or time-varying mood. This needs `add-timestamped-audio-windows`.

## Capabilities

### New Capabilities
- `analysis/audio-mood-scores`: gated, versioned mood probes and raw per-asset valence/arousal scores with provenance. User-relative percentiles are computed on read.

### Modified Capabilities
None.

## Impact

- **Observed:**
  - The probe code is a numpy ridge in `services/audio-lab/src/audio_lab/mood.py`, on branch `feat/mood-probe-benchmark`. Production has no probe table.
  - Embeddings live in `audio_embeddings` (`sidetrack/analysis/models.py`). There is one pooled vector per asset, from the first 180 s only (`sidetrack/analysis/embeddings/audio.py`).
  - Benchmark splits were not artist-grouped. Predicted valence and arousal correlate at 0.88 on the owner's library (`docs/AUDIO-BENCHMARK.md` on the branch).
- **Assumed:** CPU scoring of about 1k assets takes seconds; this will be measured in task 2.
- **Prerequisite:** the mood gate's owner listening check and decision (tasks 4.2–4.3 of `add-mood-probe-benchmark`). The evaluation follows the protocol in `add-music-analysis-evaluation-protocol`.
- Affected: `sidetrack/analysis/`, `migrations/`, `sidetrack/audio.py`, `docs/AUDIO.md`, `docs/status.yaml`.
- Licence: DEAM annotations and MuQ-MuLan weights (CC BY-NC) restrict use, so scores are for personal, non-commercial use only.
- Research: `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md` §3 and §6.3.
