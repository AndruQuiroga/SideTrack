# Proposal

## Why

The owner passed the mood check and asked for something better than two axes. A first
measurement supports that. On the 703 embeddings of run `20261027-031711-c7c3698`, about 27
principal components stand above shuffled data, and valence and arousal together explain 12.6% of
the embedding variance. Mood is real, but it's a small part of what MuQ-MuLan hears, and its two
scores correlate at 0.88 on this set.

Sidetrack's drafts each add one lens: mood, themes, facets, text search, eras. None asks which
dimensions actually organise this listener's music. This change finds that out in the audio lab,
so a product feature can rest on dimensions the owner has heard and named, not on a vocabulary
borrowed from a dataset of other people's music.

## What Changes

- **`audio-lab dimensions`** finds the independent directions in the owner's own tracks: one vector
  per track, control seeds excluded, with a shuffled baseline, and a stability check by resampling.
- **Rotated axes** make each dimension easier to hear, and the raw components stay in the output.
- **Overlap with mood:** each dimension's correlation with valence and arousal, so a dimension
  that only restates mood is visible.
- **Suggested names** from MuQ-MuLan's text tower over a small versioned vocabulary. They are
  suggestions, and a dimension with no clear term is left unnamed.
- **A blind listening review:** the extremes of each dimension, with the owner's keep, merge or
  drop and their own name, exported as a decision file.
- **A recorded result:** aggregate figures and the owner's decision in `docs/AUDIO-BENCHMARK.md`,
  with a recommendation for which dimensions a later product change should carry.

Out of scope:

- Production code, tables, jobs, routes, pages or bot output. Nothing reaches a user here.
- The product design of a combined signature. That is a later change, once this result exists.
- Non-linear models, fine-tuning or training on feedback. A linear view is cheap and auditable.
- Clustering (`add-sound-themes`). Dimensions are continuous, and themes are groups.
- Measured facets such as tempo or key (`add-track-facet-card`). The later signature can combine them.
- Calling any dimension a fact about the listener or a genre.
- Committing track lists, per-track scores or artist names to this public repo.

## Capabilities

### New Capabilities

- `analysis/sound-dimensions`: audio-lab analysis of a listener's own embedding dimensions, their
  stability, overlap with mood, suggested names, owner review and recorded result.

### Modified Capabilities

None.

## Impact

Current state:

- **Observed:** `services/audio-lab` reads Parquet runs and `mood.py` fits numpy probes. Core
  dependencies are numpy, pyarrow, soundfile and soxr, so this needs no new core dependency.
- **Observed:** run `20261027-031711-c7c3698` holds 703 MuQ-MuLan vectors, 512-dimensional,
  including previews beside full tracks and the Deezer genre control set
  (`E:/sidetrack/benchmark-v2/`). So the 27 and 12.6% above are first estimates, and this change
  recomputes them on one vector per owner track.
- **Observed:** vectors are pooled over at most the first 180 s (`w10-t3-cap180-fp32-mean-l2-v1`),
  so nothing here describes later parts of a track.
- **Observed:** `predictions.csv` holds the valence and arousal scores outside the repo.
- **Observed:** the MuQ-MuLan adapter embeds audio only (`adapters/models.py`); the text tower is
  unused. `add-sound-themes` plans a production text path, which this change doesn't depend on.
- **Assumed:** the owner's distinct full tracks number about 250 to 440, enough for a stable top
  few dimensions. The stability check measures this, and fewer stable dimensions is a valid result.
- **Assumed:** MuLan's text tower loads on the RTX 5070 through the `models` extra. Task 3.1
  confirms it.

Affected:

- `services/audio-lab/src/audio_lab/` (`dimensions.py`, CLI, text encoding in the adapter), tests.
- `docs/AUDIO-BENCHMARK.md`, `services/audio-lab/README.md`, `docs/status.yaml`.

Dependencies: none required. `add-music-analysis-evaluation-protocol` supplies the record format
when merged, and any later user-facing claim must pass its gate.
