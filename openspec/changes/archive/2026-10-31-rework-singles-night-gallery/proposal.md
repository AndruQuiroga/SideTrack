# Proposal

## Why

The owner selected the Song gallery direction and clarified that songs must be visible directly on the Singles Night home page, without opening each night. Observed: `apps/web/app/club/singles/page.tsx` currently fetches summary-only session records; `components/singles-archive.tsx` renders night links, while the separate detail page allocates most space to rating lists and often-empty final-rating columns.

## What Changes

- Make `/club/singles` an artwork-led song gallery grouped by night, newest first. Render the first batch of songs immediately; older batches append on the same page.
- Use equally weighted song cards: large square artwork, title, artist, submitter, a small labeled first-listen summary and an inline listener-impressions expander. Keep existing direct night links available as secondary navigation.
- Omit unused final-rating sections; show final ratings separately when actually present. Retain missing-artwork, missing-attribution and unavailable states.
- Add API-computed per-song first/final rating summaries so card scores satisfy existing data-honesty requirements. Preserve individual rating precision and attribution.
- Match the existing Journal shell and typography; the gallery mockup is the selected direction, adapted from one night to the home-page feed.
- Out of scope: public sharing/access changes, music playback, voting or editing, invented winners/rankings, new artwork recovery, search/filter systems, global application redesign, new services or schema migrations. Production deployment is separate from implementing and reviewing this UI change.

## Capabilities

### New Capabilities

- `web/singles-gallery`: Browse songs across nights directly on the Singles Night landing page, expand impressions inline and load older nights without opening their detail pages.
- `club/singles-summaries`: Provide honest per-phase song-rating summaries from stored Singles Night ratings under existing member access rules.

### Modified Capabilities

None. `web/data-honesty` and `web/authenticated-pages` remain unchanged and constrain this work.

## Impact

`apps/web/app/club/singles/`, shared Singles Night components/styles and server-only read models; an authenticated server action for older/retry batches; `sidetrack/club/routes/singles.py`, Singles Night read schemas, generated client and additive API contract fixtures; Python/API and web behavioral/visual tests; status documentation. Existing imported records, artwork provenance, source URLs and member-only access are preserved. Initial batch size eight includes all seven currently stored nights; existing endpoints suffice apart from additive computed summary fields.
