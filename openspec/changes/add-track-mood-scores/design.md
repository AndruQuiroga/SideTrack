# Design

## Context

See proposal.md (Why, Impact) and docs/research/MUSIC-ANALYSIS.md.

## Decisions

1. **Tables** `mood_probes` and `audio_mood_scores(asset_id, probe_id, valence, arousal, valence_pct, arousal_pct)`; analysis-owned. Alternative: columns on `audio_embeddings` (rejected: couples probe and embedding versions).
2. **CPU scoring** with numpy in the CPU worker's `embeddings` extra; the API reads stored numbers only.
3. **Export format**: audio-lab writes `probe.json` (weights, mean, scale, alpha, provenance); production loads it. No training code in production.
4. **Percentiles** recomputed in SQL (`percent_rank()`) after each scoring run.

## Risks / Trade-offs

- [DEAM shift to bass music] ? percentiles and the owner's listening check; never absolute claims.
- [V/A correlate 0.92 on this library] ? documented; visuals label the diagonal.
