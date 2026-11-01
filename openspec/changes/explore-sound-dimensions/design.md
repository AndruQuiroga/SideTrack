# Design

## Context

See proposal.md. The first measurement used every vector in a benchmark run, so previews count
twice and control tracks pull the axes toward chart genres. The owner wants to hear these
dimensions, so each must be stable enough that its two ends sound different.

## Goals / Non-Goals

**Goals:**

- Say how many dimensions of this library are real, and how many the owner can hear.
- Show what mood already covers and what it misses.
- Leave a decision a later product change can build on.

**Non-Goals:**

- Choosing a UI, or a single score that sums a person up.
- Generalising to other listeners. A club member's axes would differ, and that's a later question.

## Decisions

### Decision 1: One vector per owner track

Input is a run, a manifest and an optional `--exclude-seeds` list (the control CSVs). A track with
a full asset uses it, and otherwise its preview. Keeping both would make each track its own
near-duplicate and inflate the first components. The run's `kind` and the manifest's artist and
title give the grouping, and the report counts what was dropped and why.

### Decision 2: PCA on centred vectors, against a shuffled baseline

SVD in numpy. Parallel analysis shuffles each column independently and keeps components above the
95th percentile of 100 shuffles. Alternative: a fixed variance threshold, rejected because it
always returns an answer, even for noise.

### Decision 3: Stability before listening

For each kept component, 200 bootstrap resamples of tracks are aligned to the full fit by absolute
cosine. A component is `stable` at a median of 0.80 or more. The threshold is a working rule, chosen
before any result, and the report prints the value so it can be judged. Unstable components are
reported and left out of the review.

### Decision 4: Varimax rotation for listening

PCA orders directions by variance, and one axis can blend several ideas. Varimax on the stable
components gives axes that are easier to hear. Both are written, and the review uses the rotated
axes. Alternative: ICA, rejected as a new dependency with no evidence it would be clearer.

### Decision 5: Overlap with mood is reported, not removed

Each axis gets its correlation with valence and arousal, and the share of the embedding variance
mood explains is reported on the same track set. An axis that restates mood stays visible, because
the owner may prefer its framing. The owner decides merges.

### Decision 6: Names are suggestions with abstention

`vocabulary.csv` holds versioned terms outside any model output. Terms are scored by a contrast:
mean cosine with the axis's top tracks minus its bottom tracks, compared with a permuted-track
null. An end with no term above the 95th percentile is `no_confident_label`. Names never appear in
the blind review, so they can't lead the owner.

### Decision 7: A blind review page

`audio-lab dimensions-review` writes a local, self-contained page, like the duel report: 10 tracks
from each end with clips from 35%, the two ends in random order, and no scores or suggested names.
The owner marks each axis keep, merge or drop and writes their own name, then exports
`dimensions-decision.json`. Output refuses a path inside the repo.

### Decision 8: The repo gets aggregates only

Counts, variance shares, stability, mood correlations and the owner's axis names go in
`docs/AUDIO-BENCHMARK.md`. No track or artist names do, because that is personal listening data in
a public repo.

## Risks / Trade-offs

- [Too few tracks for stable axes] → Decision 3 reports it, and two or three stable axes is a fine
  answer. The change can be rerun on production's 862 assets.
- [Axes are really genre] → Likely for the top axes, and useful: the owner hears it, and a later
  signature can pair them with themes. Nothing here calls an axis a mood.
- [First 180 s only] → Stated in the report and the benchmark record.
- [The owner hears a pattern that isn't there] → The review is blind, and each end's tracks come
  from the model, so a name can't steer selection.

## Open Questions

- Which dimensions a product should show, and how they combine with mood, themes and facets. This
  change's result is the input to that proposal.
