# Proposal

## Why

The deployed archive has no historical weeks although the club's Discord exports contain real nominations, winners, ratings and Singles Night sessions. Recover that history through a reviewable, repeatable import that preserves authorship and source references without fabricating missing results or replaying old notifications.

## What Changes

- Add an operator-only local JSON import workflow: inspect, generate a dry-run plan, review explicit corrections/mappings, apply the exact reviewed plan, and verify the result. Planning is offline and does not change the database.
- Import album weeks, explicit winner identities, nominations and ratings into the existing club records. Parse numeric and Unicode-star ratings on the source 1–5 scale; preserve review, favorite track and original timestamps.
- Track source file hashes, Discord guild/channel/thread/message identities and reviewed corrections to make retries safe and conflicting changes visible. Reuse linked Discord identities; historical attribution must not grant membership or overwrite current account settings.
- Add separate Singles Night sessions, song submissions and phase-specific ratings, with member-only API reads and a read-only Singles Night archive linked from Club. Keep its numbering separate from album weeks. Preserve unresolved song references as observed source metadata rather than inventing catalog albums.
- Apply the owner-confirmed Singles Night week 7 correction to **2026-01-14**, retaining the original label and correction provenance. Other ambiguous dates, author labels, album identities and rating phases require explicit review.
- Persist imported weeks as historical and suppress all reminder, outbox and background-job creation during import and subsequent reconciliation of those records.
- Test on migrated throwaway Postgres, including a second identical import, before an approved production run with a fresh backup and scoped recovery instructions.

### Observed current state

- `sidetrack/club/models.py` has album weeks, nominations and ratings with Discord thread references, but no Singles Night or source-import ledger. `sidetrack/catalog/models.py` requires every catalog track to have an album.
- `sidetrack/identity/__init__.py` exposes identity read models, not a transaction-owned historical provisioning operation; existing catalog resolution in `sidetrack/catalog/metadata.py` can call external providers and commit.
- `sidetrack/club/routes/weeks.py` reconciles notifications on ordinary changes; that HTTP write path must not be used unchanged for a historical import.
- `apps/web/app/lib/api/weeks.ts` requests winner-bearing weeks for `/club`. Incomplete weeks remain accessible as real weeks without becoming invented archive winners. `ClubTabs` currently has no Singles Night destination.
- Local export evidence is `.tmp/club-history/raw-20261028-095651/{manifest.json,PREVIEW.md}`: 45 source files, 522 distinct message IDs, 36 album threads across weeks 1–10, seven Singles Night threads and two supporting text channels. Eight winner threads and eight ratings threads exist. Raw files are ignored and must not enter Git, specs or fixtures.

## Capabilities

### New Capabilities

- `club/history-import`: Validated local export ingestion, deterministic dry-run review, attribution, provenance, atomic/idempotent application, conflict handling and operational verification.
- `club/singles-nights`: Separate historical song sessions, submissions and first/final ratings, available through member-only read APIs and a read-only web archive.

### Modified Capabilities

- `club/durable-notifications`: Historical imported weeks remain excluded from schedule reconciliation and notification delivery.

## Impact

Proposed Python areas: an operator command outside the domains (following `sidetrack.club_admin`), club-owned import persistence/parser/services, public transaction-safe identity/catalog operations, schemas, policies and Alembic migrations. Web and generated API-client changes add Singles Night reads and navigation. Existing membership, privacy, account-deletion, data-honesty and module-boundary contracts remain mandatory.

No new infrastructure, dependencies or scheduled acquisition is proposed. No private ballots are reconstructed from polls/reactions. Full Discord conversations, unrelated channels, attachments/audio downloads, live Discord synchronization, automatic metadata enrichment, new membership grants, and web participation/editing controls are out of scope. Raw conversation remains in the local export archive; production receives only reviewed structured club records and minimal provenance.
