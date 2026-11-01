# Design

## Context

See proposal.md and `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md` §3, including the validation protocol and the mood-probe results.

Observed facts:
- DEAM splits were not artist-grouped, so the absolute R² may be flattering.
- Human valence and arousal ratings correlate at 0.57, held-out predictions at 0.83, and predictions on the owner's library at 0.92.
- The owner's library is mostly electronic and bass music, unlike DEAM.

## Goals / Non-Goals

**Goals:**
- Versioned, reproducible raw scores.
- An explicit human gate before any score can be read.
- Percentiles that are honest about their reference population.

**Non-Goals:**
- Felt mood.
- GEMS categories.
- Time-varying mood.
- Training in production.

## Decisions

1. **Tables.** `mood_probes(id, model, revision, pipeline, dataset, metrics json, artist_grouped bool, va_correlation, weights, mean, scale, status, gate_decision, gate_notes, gate_decided_at)` and `audio_mood_scores(asset_id, probe_id, valence, arousal)`. Both are analysis-owned. Alternative: columns on `audio_embeddings`. Rejected because it couples probe and embedding versions.
2. **No stored percentiles.** The previous draft stored `valence_pct`/`arousal_pct` per asset over all scored assets. That is a global, cross-user population, which notes §6.3 rejects. Percentiles are instead computed in SQL at read time with `percent_rank()` over the requesting user's eligible assets. "Eligible" means linked plays that are not excluded by autoplay review; see `import-listenbrainz-history` and `resolve-listens-to-audio`. Alternative: materialise percentiles per user. Deferred until read latency is measured.
3. **Minimum reference population.** 30 assets is a product rule for showing percentiles. It is not a statistical guarantee. Raw values are still returned below it.
4. **Gate record.** The audio-lab export (`probe.json`) carries metrics. The operator records the owner decision with `python -m sidetrack.audio mood-gate --probe <id> --decision accepted|rejected --notes ...`. The listening check uses extreme and mid-range tracks from the owner's library, per notes §3 step 5.
5. **CPU scoring.** Scoring uses numpy in the CPU worker's `embeddings` extra. The API reads stored numbers only.
6. **Export format.** Audio-lab writes `probe.json` (weights, mean, scale, alpha, provenance, metrics). Production has no training code.

## Risks / Trade-offs

- **DEAM shift to bass music.** Mitigated by the owner gate, user-relative percentiles and out-of-domain examples in the evaluation record. Never make absolute claims.
- **Valence and arousal correlate at 0.92 on this library.** This is recorded on the probe. Visuals label the diagonal, and the two axes must not be presented as independent findings.
- **Non-grouped splits inflate metrics.** This is recorded via `artist_grouped=false`. Re-run with grouped splits when artist metadata exists.
- **First-180-s embeddings.** Scores describe at most the first three minutes. Reads expose analyzed duration via the embedding record.

## Open Questions

- Should the owner gate also require a minimum agreement rate on pairwise judgments, as in MusAV-style relative evaluation? Decide in `add-music-analysis-evaluation-protocol`.
