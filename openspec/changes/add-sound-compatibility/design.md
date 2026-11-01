# Design

## Context

See proposal.md (Why, Impact) and docs/research/MUSIC-ANALYSIS.md.

## Decisions

1. **Overlap** = mean of each user's track-to-other-library max cosine, play-weighted, compared against a shuffled baseline.
2. **Translation** = per artist centroid, nearest artist centroid in the other library.

## Risks / Trade-offs

- [Score read as a verdict on people] ? labels 'low/moderate/high' with n; no personality framing.
