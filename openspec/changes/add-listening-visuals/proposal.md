# Proposal

## Why

Profiles are only useful once a person can see them. `docs/research/MOCKUPS.md` sets out the weekly card, mood trail, theme river, taste galaxy, listening clock and track card. The research (notes §4, "Visual vocabulary and accessibility", and §6.6) adds constraints:
- 2-D projections distort the 512-dimensional geometry, so neighbours must come from the original space.
- Missing weeks are gaps, never interpolations.
- Colour is never the only channel; each chart has an accessible list or table alternative.
- Analysis states such as "no audio" or "stale model" are distinct, never plausible defaults.

## What Changes

- Web pages under `/listening/mirror` and `/tracks/{id}`, rendering stored profiles, themes, a 2-D map and track analysis. Each chart has a table or list alternative, and each value states its n and coverage.
- A taste galaxy built from stored 2-D coordinates. Each projection is versioned by embedding model and revision, pipeline, corpus snapshot, projection method and parameters, and seed. It is labelled as a distorted overview. Selecting a point lists neighbours computed in the original vector space.
- A weekly Discord card, sent by **direct message** to opted-in users through the durable notification outbox. Reaction check-ins arrive in that DM, so check-ins stay private.
- API read routes for these views, with personal-data policies.

Out of scope:
- New analysis computation beyond the 2-D projection coordinates.
- Audio playback (ADR 0007).
- Facets beyond mood on the track page (`add-track-facet-card`).
- The sound-world explorer (`add-sound-world-explorer`).
- Coverage controls (`add-audio-coverage-review`).
- Sharing (`add-share-consent`).

## Capabilities

### New Capabilities
- `web/listening-mirror`: the listening mirror pages, honest empty states, projection labelling and accessible alternatives.
- `club/weekly-card`: the opt-in weekly Discord DM card and private reaction check-ins.

### Modified Capabilities
None.

## Impact

- **Observed:** `web/data-honesty` already forbids invented data on API failure (`openspec/specs/web/data-honesty/spec.md`). The durable notification outbox exists (`openspec/specs/club/durable-notifications/spec.md`).
- **Assumed:** the bot can send DMs to opted-in members. Members who block DMs get no card; this is reported, not retried indefinitely.
- Depends on `add-weekly-listening-profile` and `add-sound-themes`.
- Affected: `apps/web`, `apps/bot`, `packages/api-client`, API routes, docs.
- Research: notes §4 and §6.6; mockups 1–6 and the anti-patterns.
