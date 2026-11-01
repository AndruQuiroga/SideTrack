# Design

## Context

See proposal.md and `docs/research/MUSIC-ANALYSIS-RESEARCH-NOTES.md` §4 ("Self-report and autoplay cautions") and §6.5.

The earlier draft proposed a 2,000-resample bootstrap interval. That interval is removed: weekly observations are temporally dependent, so an ordinary bootstrap is not valid. No fixed number of check-ins guarantees a narrow interval.

## Goals / Non-Goals

**Goals:**
- Every value states its denominator, exclusions, timezone and versions.
- Check-ins are private and fully controllable by their owner.

**Non-Goals:**
- Statistical inference about the listener's emotions.
- Lagged or causal analysis.
- Clinical framing.

## Decisions

1. **Table.** `weekly_profiles(user_id, week_start, timezone, version, coverage json, measures json)`, recomputed per user by a CPU job after imports, link changes, autoplay overrides or timezone changes.
2. **Inclusion.** A play is included unless its session's effective classification is autoplay. The effective classification is the user override if one exists, otherwise the rule flag; see `import-listenbrainz-history`. `unclassified` sessions are included. Exclusions are counted per reason.
3. **Novelty** is the cosine distance of the week's play-weighted centroid from the 52-week qualifying centroid. **Repeat rate** is the share of included plays of tracks heard before that week, among imported history. Both are labelled relative to the imported range.
4. **Thresholds** (20 plays with audio, 8 baseline weeks, 8 paired check-in weeks) are product rules stored with the profile version. They are not significance thresholds.
5. **Association.** Same-week Spearman rho with n and the paired points only. Ties use average ranks, and constant input returns `undefined_constant_input`. Intervals that respect autocorrelation (block bootstrap, permutation with circular shifts) are an open question. They are not shipped without evaluation.
6. **Check-in storage.** A separate `mood_check_ins` table, with its own authorization policy, export route and delete route. It cascades on account deletion.

## Risks / Trade-offs

- **Over-reading weak associations.** Mitigated by copy rules in `docs/research/MOCKUPS.md` §8, the visible n and paired points, and no intervals.
- **Autoplay heuristic errors.** Users can review and override, and exclusions are disclosed.
- **Imported history incomplete.** "Repeat" and "novelty" are relative to the imported range, which is disclosed.
- **Selection bias.** People may check in mostly in unusual weeks. This is disclosed in the UI copy.

## Open Questions

- Which interval method, if any, is valid for this data at realistic n?
- Should lagged associations (listening the week after) be offered later?
