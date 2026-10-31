# Design

## Context

See proposal.md - Why. `audio-lab embed` reads a manifest and writes `embeddings.parquet` plus `run.json` with each model's revision. Its manifest requires a SHA-256, a `kind` of `full` or `preview`, and an artist and title. Run `20261027-031711-c7c3698` holds all four models on the owner's 704 assets. The lab's core install has numpy and no scikit-learn.

## Goals / Non-Goals

**Goals:**
- A defensible answer on whether MuQ or MuQ-MuLan predicts perceived mood better, and whether either is good enough to build on.
- The owner's own music as a sanity check, because DEAM's Creative Commons catalogue doesn't sound like their library.

**Non-Goals:**
- Beating published emotion-recognition results.
- Dynamic, per-second emotion. Weekly profiles use one value per track.

## Decisions

### 1. DEAM as the dataset

Use DEAM's static per-song ratings: 1,802 clips rated for valence and arousal on a 1 to 9 scale. Its manual gives a non-commercial Creative Commons licence, which fits this personal project, and its audio is included.

PMEmo has 794 pop choruses, but its licence terms couldn't be confirmed, and its downloads are mainly Baidu and Google Drive. It's the fallback, after a licence check. MTG-Jamendo has mood tags rather than valence and arousal ratings, so it can't answer this question directly.

DEAM's site refused connections from the tool used during planning. Task 1.1 confirms the download and terms before any code depends on them.

`deam_ref`: Aljanaki, Yazdani and Soleymani, "Developing a benchmark for emotional analysis of music", PLoS ONE, 2017.

### 2. Reuse `embed` rather than a mood-specific pipeline

`emotion-manifest` writes a normal manifest, with each clip's real SHA-256, `kind=full`, `source=deam` and the song ID as `source_id`. `embed` then needs no change, so vectors come from the same windows and pooling as production.

### 3. Numpy ridge regression

Closed-form ridge on standardised embeddings, solved through an SVD so testing many alphas is cheap. The probe is simple enough to fit in a few lines, and adding scikit-learn would bring a dependency into a deliberately small core install.

### 4. Repeated grouped cross-validation

Five repeats of 5-fold cross-validation, with alpha chosen by inner folds on training clips only. Groups use the artist where DEAM's metadata gives one, and the clip otherwise, so one artist can't sit on both sides of a split. R² is computed over all held-out predictions in a repeat, and reported as mean and standard deviation across repeats.

### 5. Paired bootstrap

Both models predict the same held-out clips, so the comparison resamples groups and recomputes the mean R² difference. A 95% interval that excludes zero calls a model ahead. Otherwise it's a tie, and a tie favours the model already in production.

### 6. Pass gate

Recorded in `docs/AUDIO-BENCHMARK.md` with the same "change it with a dated note" rule as the existing gate:

1. Arousal R² of at least 0.50 and valence R² of at least 0.35, out of sample, each beating the baseline. Valence is known to be harder to predict than arousal.
2. The owner hears the top and bottom 20 of their library on each dimension and agrees the extremes are broadly right.
3. The owner's decision is recorded with the run ID.

The thresholds are starting points chosen before seeing results, so they can't be fitted to them.

If MuQ-MuLan passes or ties, it stays. If MuQ is clearly ahead, the owner chooses between adding it as a mood model and accepting the smaller score. If neither passes, weekly profiles shouldn't present mood as a measured value.

### 7. Probes stay in the lab

The change writes scores and predictions only. A production probe needs its own versioning and spec, and that belongs in the weekly profile change, once this result says it's worth building.

## Risks / Trade-offs

- **Dataset shift.** DEAM's music differs from the owner's library, which leans on slowed edits and melodic bass. Mitigation: the owner's listening check is part of the gate.
- **Perceived emotion isn't felt mood.** DEAM raters judged the music, so this says nothing yet about the listener. Mitigation: the product vision's self-reports remain the real test.
- **45-second clips.** DEAM clips are short compared with production's 180-second cap. Both are pooled from 10-second windows, so the scales are comparable, but it's a known difference.
- **Non-commercial licences stack.** DEAM and MuQ-MuLan are both non-commercial, so any shipped probe stays personal-use only.

## Open Questions

None that change what gets built. Availability of DEAM is a blocker to check, handled by task 1.1.
