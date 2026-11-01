# Proposal

## Why

This is the core of `docs/PRODUCT-VISION.md`. Each week becomes a profile of perceived mood, themes, repeat versus exploration, and listening context. The profile is described against the listener's own baseline. An optional private self-report lets the listener explore whether their listening tracks how the week felt. The research (notes §4 and §6.5) shows that each number needs an explicit denominator, timezone and inclusion rule. Thresholds are product rules, not statistical guarantees, and correlations over dependent weekly data must not get a naive bootstrap interval.

## What Changes

- Weekly profiles per user. Each one has:
  - play-weighted perceived mood from `add-track-mood-scores`;
  - theme shares from `add-sound-themes`;
  - repeat rate and novelty;
  - an hour-of-day histogram;
  - an explicit coverage block: total plays, plays included, plays excluded by reason, plays with usable audio, analyzed duration and probe/model versions.
- Inclusion rules stated per measure. Plays in sessions whose effective classification is autoplay are excluded and counted as excluded. The listener can review and override that classification (`import-listenbrainz-history`). Plays are never silently dropped.
- Baseline-relative z-scores against the trailing 52 qualifying weeks, with minimum-data rules labelled as product rules.
- Weekly check-ins (valence 1–5, energy 1–5) via API. They are private by default, exportable and deletable separately from listening data.
- An exploratory association read model. It shows paired weeks, Spearman rho and n, with no confidence interval, because a naive bootstrap is invalid for autocorrelated weekly data. It is a same-week comparison only and never claims causality.

Out of scope:
- Visuals and Discord delivery (`add-listening-visuals`).
- Listening eras (`add-listening-journey`).
- Any diagnosis, wellbeing or clinical claim.
- Inferring the listener's mood from audio. Mood values here describe perceived emotion in the music.
- Lagged correlations and intervals for dependent data. These are an open question.

## Capabilities

### New Capabilities
- `analysis/weekly-listening-profile`: weekly, baseline-relative listening profiles with explicit coverage and inclusion rules.
- `analysis/mood-check-ins`: optional private weekly self-reports, their export and deletion, and an exploratory association with listening.

### Modified Capabilities
None.

## Impact

- **Observed:** `docs/STATUS.md` lists taste profiles as a stub. The stub `taste_profiles` model is in `sidetrack/analysis/models.py`.
- **Assumed:** the user timezone preference arrives with `import-listenbrainz-history` (`identity/user-preferences`).
- Depends on `import-listenbrainz-history`, `resolve-listens-to-audio`, `add-track-mood-scores` and `add-sound-themes`.
- Affected: `sidetrack/analysis/`, routes, migrations, `docs/AUTHORIZATION.md`, `docs/status.yaml`.
- Research: notes §4 ("Self-report and autoplay cautions"), §6.5; mockups 1, 2, 5 and 8.
