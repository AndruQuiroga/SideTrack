# Design

## Context

See proposal.md, `docs/research/MOCKUPS.md` §7, and `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md` §4 and §6.7.

An earlier draft planned "low/moderate/high" labels. They are removed: the labels were not validated, and they read as a verdict on people.

## Goals / Non-Goals

**Goals:**
- An exploratory side-by-side comparison with visible coverage.
- Revocable consent.

**Non-Goals:**
- A compatibility score.
- Personality claims.
- Recommendations.

## Decisions

1. **Overlap (method detail).** The mean of each user's track-to-other-library maximum cosine, play-weighted over eligible plays. It is compared against a shuffled baseline, made by sampling equally sized track sets from both libraries combined. It appears in a method-details section, not as a headline.
2. **Shared and distinct sound-worlds.** Themes whose members come from both libraries above a share threshold are shared. The others are distinct examples for one side. These are suggestions, with representative tracks.
3. **Bridge candidates.** The minimum of the track's similarity to the two users' eligible-track distributions, measured as the mean of its top-k neighbours in each library. Show the top 5. Users nominate or dismiss.
4. **Consent.** A per-user opt-in flag, plus a per-comparison check at read time. Withdrawal triggers deletion of derived rows in the same transaction. Account deletion already cascades `compatibility` rows; the new tables cascade too.
5. **Artist translation.** For each artist centroid, find the nearest artist centroid in the other library. Deferred: it needs artist identity quality from `resolve-listens-to-audio` and its own evaluation.

## Risks / Trade-offs

- **Unequal coverage.** Coverage is always shown, and a side below the threshold yields `not_enough_listening`.
- **Read as a judgement of people.** Mitigated by side-by-side framing, no score, and copy rules.
- **Model-relative similarity.** Method details name the model revision.

## Open Questions

- Should a user be able to limit which time range of their history is compared?
