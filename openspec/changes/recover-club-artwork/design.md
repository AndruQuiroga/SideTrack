# Design

## Context

See proposal.md for motivation and specs/catalog/artwork-recovery/spec.md for the behavior contract. Observed: albums already have `cover_url`, but historical album creation deliberately performs no provider requests. SinglesSong has an optional music link and no artwork field. Source plans retain music identity but no exported embed images; source preview counts are not distinct cover counts or a guarantee of recoverability.

Observed: `sidetrack/club/history/store.py` hashes all mapped song columns. Adding a column directly to SinglesSong changes old target hashes even before recovery. Existing `enrich_album` also updates unrelated metadata and uses permissive search ranking; calling it wholesale would exceed this change's artwork-only scope.

## Goals / Non-Goals

**Goals:** Reuse existing album presentation and catalog/provider boundaries, preserve the approved import and its verification, and make one-time production changes independently inspectable and reversible.

**Non-Goals:** Provider image mirroring/proxying, arbitrary image ingestion, changing history hashes, inventing track/catalog relationships, refreshing all metadata or running provider requests during web rendering.

## Decisions

1. **Provider discovery is a separate operator step.** Introduce an artwork CLI with preview/check/apply/verify. Preview consumes selected existing target identities and optional private reviewed source-link mappings; it stores a canonical local report with exact target ID, artist/title, provider entity, artwork URL, lookup evidence and status. Check binds candidates to current database values and produces an immutable digest. Apply has no external requests and locks/rechecks targets in one transaction. A recovery receipt makes identical retries no-ops. Alternatives: automatic enrichment on page load creates latency and unpredictable writes; re-running the original history import confuses source identity with metadata enrichment.

2. **Exact links first; conservative search fallback.** Normalize only supported Spotify album/track links to canonical IDs. Resolve exact entity metadata via the existing client-credentials adapter; Spotify oEmbed can supply an image for an exact supported link without user OAuth. Confirm returned artist/title against the selected record using conservative normalization; oEmbed alone does not prove artist identity when metadata is insufficient. Missing-link albums use artist/title search, with unambiguous normalized title/artist and edition compatibility; otherwise require an explicit private reviewed selection. MusicBrainz/CAA is a fallback for reviewed release-group identities, respecting existing global pacing and ADR 0005 bulk-lookup boundaries. Do not invent MBIDs or select the first fuzzy result. No provider credentials are assumed available until the private operator preflight checks presence without revealing values.

3. **Store URLs and evidence, not image blobs.** Validate HTTPS endpoints, bounded image responses and allowed provider CDN destinations. Validate each redirect before following; reject userinfo, unusual ports and private-network addresses. Cache duplicate provider lookups within one preview and honor Retry-After with a finite budget. Store provider identity, validated URL, evidence digest and timestamp in recovery-owned metadata. Retain full discovery plans privately; never expose private mappings or exports in the API. Alternatives: signed Discord attachments expire and may contain unrelated images; a local image service adds unnecessary infrastructure.

4. **Respect domain ownership and legacy hashes.** Catalog owns album-cover writes through a public operation that changes only `Album.cover_url` plus recovery evidence. Club owns a separate one-to-one `SinglesSongArtwork` row (song FK with cascade deletion) with URL/provider/evidence, avoiding changes to hashed SinglesSong columns. Operator orchestration composes public operations in one transaction and does not write another domain's tables directly. A recovery receipt tracks plan digest and changed targets for safe retry and guarded reversal. No legacy source hashes or batch digests are rewritten. Adding a direct song field was rejected because it would invalidate durable replay markers; creating fake catalog tracks merely to hold covers was rejected because source identity is incomplete.

5. **Read paths are additive.** Add nullable `cover_url` to SinglesSongRead and the generated client; join song artwork in the existing member-gated detail read. Render it in song cards using the existing AlbumArt behavior, with appropriate song alternative text and responsive sizing. Album archive/detail automatically benefit from existing `cover_url` consumers. Keep existing server-side actor/session behavior and image failure state. No provider iframe or browser-side provider credential calls.

## Risks / Trade-offs

- [Wrong edition or ambiguous identity] → Skip automatic recovery and retain a private unresolved list; allow only explicit evidence-backed selections.
- [Provider/CDN changes or future broken images] → Preserve provider identity for later re-resolution; render unavailable on failure. Recovery cannot guarantee permanent CDN availability.
- [Legacy import verification regression] → Store song artwork separately and run original history verification/replay/erasure tests before release and verification after backfill.
- [Concurrent catalog edits or deletions] → Digest-bound preconditions and locks; fail the whole application if any selected target changes. Reversal checks current artwork against the receipt and never recreates deleted records.
- [Metadata backfill leaks private source content] → Only structured identities and public music/image URLs leave the protected preparation context; synthetic test fixtures and no real-data reports in Git.

## Migration Plan

1. Add artwork/evidence/receipt tables with an Alembic migration and test metadata/schema parity against Postgres 16. Existing fields/data remain intact.
2. Test provider boundaries, atomic stale-plan rejection, repeat/no-op recovery, deletion behavior and legacy history verify/replay. Regenerate additive API contract/client, build web, test fallback and inspect synthetic desktop/mobile views.
3. Produce private production preview and exact coverage/unresolved counts; rehearse applying it to an isolated restored database. Capture a fresh production backup and protected field/count baseline before changes.
4. Publish passing images and roll out migration/API before web through the maintained Portainer stack, preserving existing stack environment, secrets, placement and unrelated services. Apply the checked artwork plan and verify coverage, original-history verification, access gates and unchanged protected fields/job counts.
5. If needed, reverse only artwork entries still matching the recovery receipt. Revert web/API images compatibly; retain additive tables. Full database restore is separate recovery because later user activity must be preserved.
