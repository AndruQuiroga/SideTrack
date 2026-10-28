# Proposal

## Why

The UX audit observed fabricated online presence in `apps/web/app/components/club-gallery.tsx` (`12 + weeks.length * 3`), generated histogram bins and unconditional live claims in `components/week-detail.tsx`. These conflict with `web/data-honesty` and make the status report's broad data-honesty claim unreliable.

## What Changes

- Remove synthesized online counts and unconditional live-listener/real-time-update claims when no supporting response exists.
- Render returned rating histogram bins exactly; missing distributions remain unavailable and zero-rating states remain empty.
- Expand regression coverage beyond banned source strings to exercise rendered output with missing and supplied aggregates.
- Preserve the UX rework as a separate change; this correction does not select its visual direction.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web/data-honesty`: explicitly cover presence, rating distributions, and real-time claims under Only computed values are displayed.

## Impact

Targets the two club components, focused web tests, and `docs/status.yaml` plus generated `docs/STATUS.md`. No API changes, migration, dependencies, or infrastructure.

Out of scope: the broader redesign, winner selection, archive sorting, provider copy, new presence endpoints, and polling infrastructure. This change is a prerequisite for releasing `rework-web-experience`; applying it remains a separate implementation step.
