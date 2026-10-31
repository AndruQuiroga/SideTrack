# Proposal

## Why

The weekly listening profile needs valence and arousal from audio, and `docs/PRODUCT-VISION.md` section 5 names mood prediction as the deciding test between MuQ and MuQ-MuLan. That test hasn't been run.

Observed:
- `docs/AUDIO-BENCHMARK.md` chose MuQ-MuLan on blind duels, genre and text-tower reasons, and nothing there measures mood.
- `services/audio-lab` has no emotion labels or supervised metric. `labels.py` covers only genre, personal and sleep labels.
- Production holds 862 MuQ-MuLan vectors, so a different model would need a new backfill. Knowing now is cheap, and finding out after building mood features is not.

## What Changes

- A command that turns the DEAM dataset into a normal audio-lab manifest and a mood label file, so `audio-lab embed` works on it unchanged.
- A `mood-probe` command that fits linear valence and arousal probes on a run's embeddings, and reports cross-validated R² per model against a mean-only baseline.
- Paired comparison of two models, with a bootstrap confidence interval, so a small gap isn't read as a win.
- Predictions over the owner's library from each probe, so the owner can hear whether "dark" and "intense" make sense on their own music.
- A mood section in `docs/AUDIO-BENCHMARK.md` with a pass gate and the owner's recorded decision.

Out of scope:
- Production mood values, stored probes, the weekly profile and check-ins. Those are later changes.
- Calling a track's mood a fact about the listener. This measures perceived emotion in the music.
- Non-linear models or fine-tuning. A linear probe tests the embedding itself, and it stays cheap on the GTX 1070.
- Re-embedding production. If the result favours another model, that's a separate decision and a separate change.
- Committing dataset audio, annotations or per-track results to this public repo. Only aggregate scores are recorded.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `analysis/audio-benchmark`: adds emotion dataset preparation, mood probes, model comparison and the mood gate.

## Impact

- Code: new `services/audio-lab/src/audio_lab/mood.py` and `emotion.py`, plus `cli.py`.
- Tests: new `services/audio-lab/tests/test_mood.py` and `test_emotion.py`, with synthetic data only.
- Docs: `docs/AUDIO-BENCHMARK.md`, `services/audio-lab/README.md`, `docs/status.yaml`.
- No new dependency: probes use numpy. No root package, API, schema or rack change.
- Data: DEAM stays on the owner's HDD under `E:/sidetrack`. Its licence is non-commercial, which fits this personal project (`deam_ref` in design.md).
- The benchmark runs on the owner's RTX 5070.
