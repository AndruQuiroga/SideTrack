# Design

## Context

See proposal.md, `docs/research/MOCKUPS.md` §1–6 and the anti-patterns, and `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md` §4 ("Visual vocabulary and accessibility") and §6.6.

## Goals / Non-Goals

**Goals:**
- Honest, accessible views of stored values.
- A private weekly touchpoint.

**Non-Goals:**
- New analysis.
- Playback.
- Shared or public cards (`add-share-consent`).

## Decisions

1. **Charts.** Rendered client-side with the existing web stack. Each chart component pairs with a table or list component fed by the same data. Patterns or shapes supplement colour, and charts honour `prefers-reduced-motion`.
2. **Projection.** A CPU job computes 2-D coordinates. PCA is the default because it is deterministic and less prone to implying false clusters. UMAP is optional, with a recorded seed and parameters. The job stores `projection_version` (model, revision, pipeline, corpus snapshot hash, method, params, seed). A new library or model invalidates it. The map is never used to compute neighbours.
3. **Gaps.** Line charts break at missing or insufficient weeks. The theme river shows an explicit gap band with an explanation.
4. **Weekly card by DM.** The previous draft did not specify where the card is posted. Reactions in a shared channel would reveal check-ins, so the card is sent by DM only. Rendering starts as a Discord embed (text); an image card is a later option.
5. **State vocabulary.** The web uses one shared component for the analysis states: no audio, not computed, uncertain link, insufficient sample, stale model, failed, unavailable.

## Risks / Trade-offs

- **Mobile galaxy performance.** Cap points, simplify labels, and default to the list view on small screens.
- **Projection misread as truth.** The notice is always visible, and neighbours come from the original space.
- **DM fatigue.** Opt-in and easy opt-out.

## Open Questions

- Should the galaxy default to the list view for everyone until the owner has evaluated it?
