# Design

## Context

See proposal.md (Why, Impact) and docs/research/MUSIC-ANALYSIS.md.

## Decisions

1. **HDBSCAN** (cosine, min cluster 8) via scikit-learn in the CPU worker extra; fallback k-means with silhouette when > 60% is noise.
2. **Calibration**: per-term z-score of similarity across the library to counter the modality gap.
3. **Vocabulary** versioned file in `sidetrack/analysis/vocabulary/`.
4. **Tables** `text_embeddings`, `sound_themes`, `sound_theme_members`.

## Risks / Trade-offs

- [Unhelpful names] ? representative tracks shown; renaming.
