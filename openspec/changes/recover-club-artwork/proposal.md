# Proposal

## Why

The recovered club archive has music identities and ratings but lacks artwork. Observed: `sidetrack/catalog/historical.py` creates bare albums; `apps/web/app/components/album-art.tsx` already renders stored album covers, while `sidetrack/schemas/singles.py` exposes no song artwork field. Recovering verified covers will make the live archive easier to browse.

## What Changes

- Add an operator-run, previewable artwork recovery flow for existing album and Singles Night records, using exact Spotify links first and conservative artist/title matches where links are missing.
- Store only verified HTTPS artwork URLs with provider identity and recovery evidence; preserve existing covers and report ambiguous or unavailable matches.
- Add optional Singles Night artwork storage, API/client fields and web rendering with an explicit unavailable state.
- Rehearse and apply a checked production backfill, then verify artwork coverage and preservation of historical data and replay safeguards.
- Out of scope: reimporting history, changing ratings/attribution, audio acquisition, automated recurring enrichment, new infrastructure, guessing covers, fetching arbitrary Discord attachments or changing account access.

## Capabilities

### New Capabilities

- `catalog/artwork-recovery`: Verified, repeatable artwork discovery and guarded backfill for existing club albums and singles, including member-facing presentation.

### Modified Capabilities

None. Existing web data-honesty and authenticated-page requirements remain applicable without changes.

## Impact

Catalog provider adapters and public artwork operations; club Singles Night artwork ownership; an additive migration; operator CLI/reports; Singles Night API schemas and generated TypeScript client; archive components/tests; rollout and status documentation. No new services or audio operations. Observed historical target hashes include all mapped columns (`sidetrack/club/history/store.py`), so additive artwork must not invalidate legacy replay markers. Private source exports and recovery plans remain outside Git.
