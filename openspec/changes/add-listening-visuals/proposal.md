# Proposal

## Why

Profiles are only useful once a person can see them. docs/research/MOCKUPS.md sets out the weekly card, mood trail, theme river, taste galaxy, listening clock and track card.

## What Changes

- Web pages under `/listening/mirror` and `/tracks/{id}` rendering stored profiles, themes, a 2-D map and track analysis.
- A weekly Discord card with reaction check-ins, delivered through the durable notification outbox.
- API read routes for those views with personal-data policies.

Out of scope:
- New analysis computation beyond storing the 2-D map coordinates.
- Audio playback (ADR 0007).

## Capabilities

### New Capabilities
- `web/listening-mirror`: the listening mirror pages and their honest empty states.
- `club/weekly-card`: the opt-in weekly Discord card and reaction check-in.

### Modified Capabilities
None.

## Impact

- Depends on `add-weekly-listening-profile`. Affected: `apps/web`, `apps/bot`, `packages/api-client`, API routes, docs.
