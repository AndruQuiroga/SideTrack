# Proposal

## Why

This is the core of docs/PRODUCT-VISION.md: each week becomes a profile of mood, themes, comfort against exploring and context, described against the listener's own baseline, plus an optional self-report to test whether listening tracks felt mood.

## What Changes

- Weekly profiles per user: play-weighted mood (from `add-track-mood-scores`), theme shares, repeat rate, novelty (distance from the 52-week centroid), hour-of-day histogram, audio coverage.
- Baseline-relative z-scores against the trailing 52 weeks, with minimum data rules.
- Weekly mood check-ins (valence 1?5, energy 1?5) via API, and a correlation read model with n and bootstrap interval.

Out of scope:
- Visuals and Discord delivery (`add-listening-visuals`).
- Any diagnosis or wellbeing claim.

## Capabilities

### New Capabilities
- `analysis/weekly-listening-profile`: weekly, baseline-relative listening profiles with coverage.
- `analysis/mood-check-ins`: optional weekly self-reports and their honest correlation with listening.

### Modified Capabilities
None.

## Impact

- Depends on `import-listenbrainz-history`, `resolve-listens-to-audio`, `add-track-mood-scores`, `add-sound-themes`. Replaces the stub `taste_profiles` usage for this purpose (docs/STATUS.md: stub). Affected: `sidetrack/analysis/`, routes, migrations, docs.
