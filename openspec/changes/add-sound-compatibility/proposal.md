# Proposal

## Why

The product vision's compatibility view compares how two people's music sounds, rather than their shared artists. This suits a club whose members rarely share obscure artists. The research (notes §4 and §6.7, mockup 7) requires the comparison to be exploratory and side by side, never a verdict. Each side's coverage must be visible. Consent must be revocable, and revoking it must remove derived data. An unvalidated cosine-derived number must not be labelled "low/moderate/high", and there is no single compatibility percentage.

## What Changes

- Opt-in comparison between two users. Both must opt in, and each person can withdraw at any time.
- Results computed from each user's eligible, embedded plays:
  - shared sound-worlds and distinct examples per side;
  - an overlap measure compared against a shuffled baseline, shown as a method detail, not a headline verdict;
  - up to five bridge candidates near both libraries, which each person can review and nominate.
- Coverage per side (eligible tracks with audio out of total), model revision and theme-build version.
- On withdrawal or account deletion: derived rows are deleted, the other user stops seeing results, and cached views are invalidated.

Out of scope:
- Recommendations beyond bridge candidates.
- Path-building between sounds (`add-sound-bridge`).
- Personality or interpersonal-compatibility claims.
- Members without opt-in or without imported history.
- Public sharing of a comparison (`add-share-consent`).

## Capabilities

### New Capabilities
- `analysis/sound-compatibility`: opt-in, revocable, audio-based side-by-side comparison of two listeners, with per-side coverage.

### Modified Capabilities
None.

## Impact

- **Observed:** a stub `compatibility` table and route exist (`sidetrack/analysis/models.py`). `identity/account-deletion` already cascades compatibility rows (`openspec/specs/identity/account-deletion/spec.md`). This change replaces the stub's meaning with real, consented values.
- **Assumed:** a consent flag fits `identity/user-preferences` from `import-listenbrainz-history`. Otherwise this change adds its own analysis-owned consent table.
- Depends on `add-weekly-listening-profile` (eligibility), `add-sound-themes` and `resolve-listens-to-audio`.
- Affected: analysis, routes, the web compare page.
- Research: notes §4 and §6.7; mockup 7.
