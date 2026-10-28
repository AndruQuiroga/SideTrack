# Design

## Context

See `proposal.md` for the observed empty archive and export inventory. Existing `Week`, `Nomination` and `Rating` records already support the album archive, but ordinary week writes reconcile notifications. Identity and catalog own their tables, and catalog resolution can make provider requests or commit. Existing ratings are unique per week/user. Catalog tracks require an album, while a Singles Night source often identifies only a song and artist.

The local inventory contains 522 distinct message IDs, numeric/star-based ratings, template messages, curated song headings and incomplete weeks. Discord author IDs are stronger evidence than display names. A source message's author can be the curator rather than the named song submitter; a bare star reply does not necessarily establish its song or whether it was a first/final rating. These cases need explicit reviewed assignments, not positional guesses.

This design stays within ADR 0001 domain ownership, ADR 0002 Postgres state and ADR 0006 Portainer deployment. It adds no infrastructure or replacement architecture.

## Goals / Non-Goals

**Goals:** deterministically transform selected source files into reviewable candidates, apply approved historical records atomically, preserve traceability, avoid duplicate/overwritten contributions, and expose Singles Night through existing member/session boundaries.

**Non-Goals:** a Discord client, general-purpose chat archive, live import schedule, automatic metadata enrichment, ballot reconstruction, playback, participation UI, or automatic interpretation of unresolved prose. Source conversations remain outside production; only structured reviewed content is imported.

## Decisions

### 1. Use an offline operator workflow with a separate target check

Add `python -m sidetrack.club_history` as an operator composition entrypoint, following `sidetrack.club_admin`. Proposed commands:

- `preview --manifest ... --review ... --output ...`: pure local parse; no DB connection or network. Output canonical JSON and readable HTML/Markdown with candidates, evidence references, gaps, unresolved items and non-record classifications. Escape all source text in HTML; permit only validated HTTP(S) provider/source links. Exclude absolute input paths and volatile timestamps from the plan digest.
- `check --plan ... --output ...`: read-only DB reconciliation. Show planned inserts, reuses, erased/skipped entries and conflicts; produce a target-bound execution plan containing the source/interpretation digests and relevant target fingerprints. No implicit "create user" decision or ambiguous match is allowed.
- `apply --plan ... --expect-digest ...`: explicit operator execution of that target-bound plan. Rehash inputs and mappings, check parser/schema version, then revalidate target preconditions inside the transaction. A changed plan needs another check/review.
- `verify --batch ...`: read-only comparison of imported targets and source ledger, aggregate counts and side-effect checks. Do not create or repair anything automatically.

Use the existing configuration/secret loading only for database access. The importer needs no Discord, Last.fm or Spotify token. Raw inputs and review plans live in the ignored local export directory; copy them to protected rack storage only for the approved rollout. Private data never becomes repository fixtures.

Alternative: directly replay HTTP writes. Rejected because it would couple identity acting-user policies, repeated commits and live schedule reconciliation to a privileged historical operation. Alternative: an API upload or background job. Rejected because a small, one-off operator workflow is sufficient and easier to review.

### 2. Separate extraction evidence from approved interpretation

Validate each manifest file hash, JSON shape, expected guild, selected parent channel and unique message identity before creating candidates. Do not follow links, fetch attachments or interpret message content as instructions. Exact repeated messages collapse to one observation; same-ID divergent content blocks preview.

Classify thread roles from source labels plus reviewed grouping. Album grouping uses the approved event/thread set, not week number alone. Anchor each group to a stable nominated source thread chosen in review, so a newly exported winner thread does not change the event identity. Singles Night uses its own source thread directly. Namespace every key by guild and event kind. Preserve original offsets; date-only labels do not acquire invented midnight event times. Use America/Phoenix for reviewed local schedules unless a source explicitly establishes another zone.

A private review mapping records exact source keys, input hashes, correction reasons, author decisions, explicit exclusions and canonical album/song fields. Seed it during implementation with the owner-confirmed Singles Night week 7 date correction to 2026-01-14, tied to that exact source thread; retain `[1-14-2025]` as the original label. Do not broadly replace all 2025 dates. Conflicting or incomplete evidence remains visible until mapped or explicitly excluded.

Recognize source mini-form fields, numeric scores and full/empty/half stars. Preserve explicit 1–5 precision; do not normalize to 10. Reject contradictory number/star forms, out-of-range values and duplicate conflicting album-week author ratings. Tutorial examples are non-records. Parse a Singles Night phase only from explicit evidence or the review mapping; unassigned stars remain unresolved. A review decision can associate a curator's heading with a verified submitter ID without changing who authored the evidence message.

Alternative: infer song/phase from chronology or match users by names. Rejected because those heuristics can attach a real person's opinion to someone else. Parser improvements must regenerate the preview; they do not silently reinterpret applied records.

### 3. Keep persistence in its owning domains and one transaction

The composition entrypoint coordinates public operations on `identity`, `catalog` and `club`, all receiving the caller-owned Session and flushing without committing. Add narrowly scoped historical identity provisioning and reviewed catalog upsert operations as needed; do not mutate another domain's exported ORM models. Club owns parsing, its ledger and business inserts. Import-linter remains enforced.

Identity matches provider=`discord` and the exact Discord ID. A reviewed new author can receive a collision-safe handle and Discord identifier link without provider credentials, membership, roles or non-private listening visibility. Existing profiles, handles and links remain unchanged. Verify identity creation does not enqueue work.

Catalog application reuses an explicitly reviewed catalog ID or an unambiguous existing provider ID/exact reviewed identity. Multiple matches require review. If no match exists, the catalog operation can store the source-backed album title/artist/year without pretending to have a MusicBrainz/Spotify ID, artwork, genres or track list. No network resolver runs during apply. Real incomplete metadata is not placeholder data; the UI already has missing-artwork behavior.

Take a transaction-scoped import lock for the selected guild and use serializable target checks/constraints to reject concurrent conflicting inserts. Keep the dataset small and apply one checked batch in one transaction, including identity/catalog changes and ledger inserts. Domain helpers must never commit independently. A serialization failure rolls back and requires a fresh check.

### 4. Add minimal provenance and protect already applied data

Proposed club-owned tables:

- `club_history_batches`: parser/plan/source-manifest digests, format version, application time and aggregate operation counts. No raw plan payload, full messages, tokens or local file paths.
- `club_history_sources`: unique stable source key and entity kind, source hashes, channel/thread/message references, target identity and post-apply target fingerprint. Corrections store only the necessary non-secret field/value/reason provenance. It is operator-only, not a public model dump.

Typed target references or explicit lookup rules must detect deleted targets; do not rely on filenames or a single global "import finished" flag. Store no redundant author names/Discord IDs or review bodies in the ledger. Source key/target fingerprint retention must permit replay detection after erasure without restoring deleted content.

An identical checked retry skips existing source keys. If the exact batch plan is retried, verify stored targets before returning already-applied. A new export adds only approved new keys. A changed source hash, independently created week/user rating collision, or edited target is a conflict; never overwrite on replay. A missing previously imported author-owned target is treated as erased and stays absent. Provision a new identity only for an approved new contribution that will actually be inserted, not for an all-erased replay.

Alternative: source IDs in free-form rating metadata only. Rejected because weeks, nominations and Singles Night also need uniqueness, conflict handling and an auditable batch boundary.

### 5. Model Singles Night separately without inventing albums

Add club-owned `singles_sessions`, neutral `singles_songs`, `singles_submissions` and `singles_ratings` tables. Sessions retain source thread, original label, independent number and reviewed date/time. Song rows hold observed title/artist/source links, session ordering and an optional verified catalog track reference; they do not require an album. Submissions hold verified submitter attribution. Ratings point to the session/song and author, with a first-listen/final phase and a unique session/song/user/phase constraint.

Separate neutral song identity from author-owned attribution: deleting a submitter must not delete another person's rating of that song. User FKs on submissions and ratings cascade; neutral songs have no copied submitter name. Imported account deletion therefore removes that user's attribution/reviews while preserving other participants' history. Apply replay suppression to erased source contributions.

Add member/bot read endpoints `GET /club/singles-nights` and `GET /club/singles-nights/{id}` with default-deny policies. Register through the API composition layer; generate the TS client using the existing generator. Add `/club/singles` and `/club/singles/[id]`, linked from `ClubTabs`, using server-only API calls and session-derived actors. Display reviewed date, observed songs, attributed submissions and separated first/final rating sections; use explicit absent/unavailable states. Keep the album `/club` query restricted to real stored winners; incomplete weeks are preserved and linked by the operator's import report.

Alternative: reuse album `Week` and force each song into an album. Rejected because number sequences overlap and the album FK would require fabricated or unsupported metadata.

### 6. Make historical silence durable

Add a non-null `Week.historical` flag, default false for existing/live records. The operator import sets it true. Ordinary HTTP schemas must not allow callers to clear it implicitly. Historical insertion uses a club-owned operation and never the normal creation route.

Guard reconciliation, production and claiming so historical weeks cannot schedule or deliver notices. Reconciliation disables accidental stale schedules and makes obsolete pending delivery ineligible. This is necessary even after import: a later admin edit or worker restart must not revive old reminders. Singles Night import creates no live schedules. Import tests compare schedule, outbox, application job and queue counts before/after; no Discord sends are part of the workflow.

Alternative: omit historical deadlines. Rejected because that loses real schedule data and is fragile when a date is later edited. Existing non-historical delivery semantics remain unchanged.

## Risks / Trade-offs

- Ambiguous free-form history → explicit local review mappings; no automatic winner, author or phase inference. The first preview is allowed to contain blocked candidates.
- Missing or edited source messages → hashes, edit timestamps and reasoned exclusions; no claim to recover deleted/inaccessible Discord history.
- New historical users → private defaults, collision checks, no memberships, and deletion/replay regression tests.
- Standalone songs without catalog albums → club-owned observed metadata, optional catalog links and honest missing artwork.
- Live writes during import → relevant-row preconditions, uniqueness and serializable apply; abort rather than overwrite. Unrelated Last.fm listens must not be treated as conflicts or removed by recovery.
- Rollback after subsequent activity → scoped batch ownership/fingerprint checks; do not blindly restore the entire production DB over newer data.

## Migration Plan

1. Implement with synthetic fixtures and a new Alembic revision after the actual current head. Additive tables and the false-default historical flag preserve existing rows; extend account-deletion and migration-drift tests. No schema change has been applied by this proposal.
2. Generate the real offline preview in ignored storage. Review author creation/matches, catalog identities, phases, date correction and explicit exclusions. Report all 522 source messages by disposition; eight winner and eight ratings threads are evidence counts, not a promised count of valid ratings or automatically importable albums.
3. Migrate throwaway Postgres 16 + pgvector, run target check/apply/verify, then repeat the import and compare entity, membership, schedule and queue counts. Inspect both archive types with a test member, a non-member and an anonymous visitor. Keep real data out of test fixtures and CI artifacts.
4. Build and publish reviewed code through CI; deploy through the existing Portainer stack while preserving current credentials, env and placement. Follow ADR 0006 for compatible API/worker/bot/client image rollout; do not modify the stack with a second writer.
5. Take a fresh protected DB backup, restore-test it in isolation and record its hash. Preserve an independent protected copy of export inputs/plans outside `.tmp`, which is disposable. Check the production target again and present exact planned changes before the production import action.
6. Apply the reviewed target-bound plan once during a controlled window. Verify source/target counts, sampled attribution and ratings, source links, Singles Night date correction, archive rendering, unchanged memberships and zero new delivery/acquisition work. Preserve a private verification report and update honest status evidence.
7. For a bad import after commit, first stop further import writes and produce a reviewed batch-scoped reversal using recorded created IDs and unchanged-target fingerprints. Remove only batch-owned contributions; preserve pre-existing or subsequently referenced identities/catalog rows and all unrelated listens/links. Any changed target blocks automatic reversal. Full backup restoration is a separately approved maintenance recovery, not the default rollback. Do not downgrade/drop populated tables before preserving the imported history.

## Open Questions

None that block this design. Exact per-message ambiguities and catalog/author mappings are expected outputs of the implementation's local preview, resolved through its specified review mechanism rather than changes to these contracts.
