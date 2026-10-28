# Historical club imports

The historical import workflow is being implemented under
`openspec/changes/import-discord-club-history`. Production import is not enabled
by this document. Never put actual Discord exports or review plans in Git.

## Source manifest

Input is DiscordChatExporter JSON plus a UTF-8 JSON manifest in its parent
directory. The manifest contains `guildId` and a `files` array. Each entry has
`file` (a relative JSON path), `sha256` (lowercase SHA-256 of exact file bytes),
and optional `channelId` which must match the file. Source paths must remain
inside the manifest directory after resolving links. Exported `messageCount`
must equal the message array length.

The operator independently selects the guild and allowed channel IDs; the
manifest cannot authorize additional channels. A thread's exported `categoryId`
must name an allowed parent channel. A normal channel's own ID must be allowed.
Only guild text/news channels and their public/private/news threads are accepted.
Each message needs a Discord ID, author ID/name, text and offset-aware timestamp.
Identical duplicate messages collapse; divergent same-ID copies block parsing.
These are integrity checks, not a guarantee that deleted or inaccessible messages
were recovered. No source links or attachments are fetched during preparation.

Raw exports and private review plans belong in ignored/protected storage.
Only synthetic sources belong in automated tests.

## Review mappings

An optional private review JSON binds to `source_digest`. Its `events` map is
keyed by thread ID; a date correction requires `original_date`, replacement ISO
`date`, and `reason`. Original labels remain evidence. Apply the confirmed
Singles Night year correction only to its exact source thread, not every 2025 date.

`records` maps candidate source keys to an exact `evidence_hash`, a `reason`,
approved `fields` patches, and the named issues those patches `resolves`.
An optional `original_fields` object must match the unpatched candidate exactly.
Date and catalog corrections retain original/replacement values and reasons in
minimal provenance; author names and review bodies are not copied into the ledger.
Alternatively an explicit `exclude` decision records a non-record reason.
`exclude_messages` records deliberate chat/non-record exclusions by message ID.
The global source digest ensures those decisions cannot silently apply to changed input.

`singles_messages` maps a message ID to its `evidence_hash`, `reason` and a
`records` array. A curated heading can yield a `singles_song` and a separate
`singles_submission`, with an explicitly verified submitter Discord ID. Ratings
must reference the song source key and explicitly choose `first` or `final` phase.
An optional `singles_rules` map, keyed by exact session thread ID, can record
the owner's approved context rule: `default_phase: "first"`,
`reply_precedence: true`, and a nonempty `reason`. This rule is bound to the
whole export digest. It applies only after an explicitly reviewed song heading.
A reply or Discord message link takes precedence over the current heading,
including replies to earlier scores. Deleted, cross-session, conflicting or
unknown references stay unresolved. An unreviewed heading interrupts the context.
Explicit `Final:` / `Final rating:` / `Re-rating:` scores use the final phase;
ambiguous prose still requires an individual assignment. Without this approved
rule, star-only replies remain unresolved without explicit assignments. Song catalog
linkage is optional; no artificial album is required. Unknown author names do
not become identity matches. Source curator and submitter are separate concepts.

## Offline preview

Run `uv run --frozen python -m sidetrack.club_history preview --manifest INPUT/manifest.json
--guild GUILD_ID --source ALBUM_CHANNEL_ID=album --source SINGLES_CHANNEL_ID=singles
--source ANNOUNCEMENTS_CHANNEL_ID=supporting --output NEW_PRIVATE_DIRECTORY` on one line,
substituting the selected IDs and paths. Add `--review PRIVATE_REVIEW.json` after
reviewing mappings. No database connection or provider credentials are required.
The CLI writes `plan.json` and `preview.html` without replacing an existing report.
The HTML escapes source text and runs no scripts or external resources. Open it
locally, not on a public web server. It includes private excerpts for review.

The report accounts for every message and shows unresolved candidates and gaps.
The digest is stable for identical sources, parser version and mappings; editing
the plan invalidates it. A preview with unresolved candidates is not ready for
database application. Database operations require the reviewed release and a
target check; the presence of a CLI command does not mean production was imported.

## Read-only target check

Run `uv run --frozen python -m sidetrack.club_history check --plan PRIVATE/plan.json
--output NEW_PRIVATE_CHECK_DIRECTORY` on one line. It uses the configured database
and a repeatable-read, read-only transaction. The resulting `checked.json` contains
private identity decisions, insert/reuse/erased/extend actions, target fingerprints,
conflicts and a new digest. Standard output includes counts and the digest only.
A nonzero exit means the plan has conflicts or the operation failed.

Existing users match by exact linked Discord ID and retain their profiles. A new
author requires an explicit `identities[DISCORD_ID]` decision with `action: "create"`
and `reason`; a reviewed display name and optional handle can be supplied there.
An existing handle belonging to another account blocks creation. Independently
stored weeks/ratings are conflicts, rather than automatic import targets.
Source edits, changed interpretations and modified imported targets also conflict.
An expanded export may fill an empty historical week thread reference, but cannot
clear an existing reference. An erased source target remains erased.

Check performs no writes and does not reserve identities or targets. The apply
operation must recheck the fingerprint immediately before its atomic writes.

## Atomic application and verification

Before production writes, preserve the selected inputs and private review/check
files outside disposable `.tmp`, take a fresh database backup, restore-test it
in isolation, and review the exact target check and digest. Use the maintained
Portainer stack release for migration and application compatibility.

Run `uv run --frozen python -m sidetrack.club_history apply --checked PRIVATE/checked.json
--expected-digest CHECKED_DIGEST --manifest INPUT/manifest.json --guild GUILD_ID
--source ALBUM_CHANNEL_ID=album --source SINGLES_CHANNEL_ID=singles
--source ANNOUNCEMENTS_CHANNEL_ID=supporting --review PRIVATE_REVIEW.json` on one
line, including every originally selected source. The command verifies source
file hashes, parses the same review again, compares the complete plan, obtains
a guild transaction lock, locks existing targets, and rechecks fingerprints in
a SERIALIZABLE transaction before writing. A failure rolls back the entire
transaction, including identity, catalog and ledger rows. It does not retry a
stale check automatically. An identical already-applied retry verifies targets
and returns the original batch. Missing erased targets stay absent.

Run `uv run --frozen python -m sidetrack.club_history verify --checked PRIVATE/checked.json
--output NEW_PRIVATE_VERIFY_DIRECTORY` on one line. Verification is read-only;
it reports reuse/erased counts and mismatches in `verification.json`. It never
repairs a mismatch. Routine stdout contains counts/digests or the batch ID,
without author names, source bodies, local paths or credentials.

Capture before/after counts for `job_schedules`, `job_schedule_occurrences`,
`club_notification_outbox`, `background_jobs`,
`job_queue.procrastinate_jobs`, and `club_members`. Import and verify must leave
these unchanged and perform no provider exchange, download or external send.
Historical reconciliation creates no schedules. Restart reconciliation disables
obsolete historical schedules before queueing; producer and claim independently
reject historical delivery. Existing live-week behavior remains covered by its
original schedule and delivery tests.

## Recovery boundary

If application fails before commit, the transaction is rolled back. For an
already committed batch, first save a verification report and stop further
import writes. There is deliberately no blind undo command. A batch-scoped
reversal must be prepared and reviewed against its source ledger:

1. Select only markers owned by the exact `club_history_batches.id`. Resolve
   each target and require its current fingerprint to equal `target_hash`.
   Any changed target blocks automatic removal; an erased target stays absent.
2. Inspect references created after the batch, including other participants'
   ratings and later batches sharing a week/song/catalog identity. Such targets
   need an explicit preservation decision before reversal.
3. Remove only approved batch-owned contributions, in dependency order, in one
   transaction. Preserve replay markers. Do not erase pre-existing users/albums
   or identities/catalog rows referenced by unrelated listens or newer history.
   Reused targets were never owned by this batch.
4. Verify the reversal and compare unaffected membership, listening/provider-link,
   delivery and queue records against the saved preconditions.

A full backup restore is separate maintenance recovery requiring review of newer
writes; it must not overwrite post-backup Last.fm imports or account links as a
routine undo. Do not downgrade/drop populated history tables to reverse a batch.

## Verification observations, 2026-10-28

The owner confirmed successful Discord sign-in and Last.fm account linking on
the public deployment. The historical archive is being prepared separately.

The Singles Night list/detail components were rendered from synthetic fixtures
with the production build's CSS at 1440 × 900 and 390 × 844. Both layouts were
inspected: navigation remains readable, the date has no invented time, source
links are visible, and first/final ratings form distinct sections. Measured
document widths matched the viewport at both sizes, with no horizontal overflow.
`apps/web/tests/render-singles-preview.cjs` reproduces these local views after
the web build. The fixture renderer and data live under `tests/`; private real
participant data is excluded from visual artifacts. Member/access and deletion
behavior are covered by the API and web integration tests listed in the change.

## Persistence

The additive history migration keeps ordinary weeks non-historical by default.
The club-owned batch/source ledger records digests and target references, not
full messages or author-name copies. Source markers survive deleted targets so
replaying an old import can recognize erasure rather than recreate contributions.

Singles Night has independent sessions, neutral songs, submissions and ratings.
Songs may remain without catalog tracks/albums. Submission attribution and ratings
belong to users and cascade on account deletion; the neutral song remains so other
participants' ratings are preserved. First-listen and final ratings have separate
unique keys. Compound song/session references reject cross-session contributions.
