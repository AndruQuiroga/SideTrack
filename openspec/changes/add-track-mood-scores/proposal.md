# Proposal

## Why

The mood probe benchmark (run `20261031-204732-9b07ff0`, branch `feat/mood-probe-benchmark`) showed MuQ-MuLan predicts DEAM valence (R? 0.615) and arousal (R? 0.688), but the probe lives only in audio-lab. Weekly profiles need per-track mood values in Postgres, versioned so a retrained probe never mixes with old values.

## What Changes

- A stored, versioned linear probe (weights, standardisation, training dataset, CV scores) for valence and arousal on one embedding model and revision.
- Per-asset mood scores computed from stored embeddings on the CPU worker (a 512?2 matrix product; no GPU, no torch).
- Library-relative percentiles alongside raw scores, because DEAM's scale doesn't transfer to the owner's music.
- An operator command to load a probe exported by audio-lab and score all embedded assets.

Out of scope:
- Presenting mood to users (weekly profile and visuals changes).
- Retraining in production; training stays in audio-lab.
- Felt mood: these are perceived-emotion estimates.

## Capabilities

### New Capabilities
- `analysis/audio-mood-scores`: versioned mood probes and per-asset valence/arousal scores with provenance and percentiles.

### Modified Capabilities
None.

## Impact

- **Observed:** probe code is numpy ridge in `services/audio-lab/src/audio_lab/mood.py` (branch); production has no probe table. Embeddings: `audio_embeddings` (`sidetrack/analysis/models.py`).
- **Prerequisite:** the mood gate's owner listening check and decision (tasks 4.2?4.3 of `add-mood-probe-benchmark`).
- Affected: `sidetrack/analysis/`, `migrations/`, `sidetrack/audio.py`, docs/AUDIO.md, docs/status.yaml. Licence: DEAM and MuQ-MuLan are non-commercial; scores are personal-use only.
