# Design

## Context

See proposal.md (Why, Impact) and docs/research/MUSIC-ANALYSIS.md.

## Decisions

1. **Table** `weekly_profiles(user_id, week_start, version, json measures)` recomputed by a CPU job per user after imports.
2. **Novelty** = cosine distance of the week's play-weighted centroid from the 52-week centroid; **repeat rate** = share of plays of tracks heard before that week.
3. **Bootstrap** 2,000 resamples, seeded for reproducibility.

## Risks / Trade-offs

- [Over-reading weak correlations] ? copy rules in docs/research/MOCKUPS.md ?8.
