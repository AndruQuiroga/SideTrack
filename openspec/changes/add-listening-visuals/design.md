# Design

## Context

See proposal.md (Why, Impact) and docs/research/MUSIC-ANALYSIS.md.

## Decisions

1. **Charts** rendered client-side with existing web stack; the galaxy uses stored 2-D coordinates computed by a CPU job (PCA by default, UMAP optional).
2. **Card image** rendered as a Discord embed (text) first; an image card is a later option.

## Risks / Trade-offs

- [Mobile galaxy performance] ? cap points and simplify labels.
