# Spec Delta

## Purpose

Recover structured club history from operator-selected Discord exports with reviewable attribution, source provenance and repeatable application, without treating missing or ambiguous messages as confirmed facts.

## ADDED Requirements

### Requirement: Source exports are explicitly selected and validated
The importer SHALL accept local DiscordChatExporter JSON with an explicit guild/channel allowlist and source-file SHA-256 manifest. It SHALL validate schema, source identity and message identity before planning. It MUST reject mismatched hashes, foreign-guild files and conflicting copies of the same message, and ignore exact duplicates without double counting.

#### Scenario: Source file changes after extraction
- **WHEN** a selected file differs from its manifest hash
- **THEN** preview fails with a file-specific integrity error and creates no database records

#### Scenario: Duplicate and unrelated inputs
- **WHEN** inputs contain an identical repeated message and a file from a different guild
- **THEN** the duplicate contributes one message and the foreign-guild file blocks the plan

### Requirement: Parsing produces a deterministic offline review plan
Preview SHALL run without database writes or external network access and produce stable machine-readable candidates plus a readable report. Every message SHALL be accounted for as evidence, a candidate, an explicit non-record, or an unresolved issue. The plan SHALL distinguish album weeks from Singles Night and report missing winners, ratings and identities without inventing them.

#### Scenario: Incomplete album history
- **WHEN** a week has a nomination thread but no explicit winner or rating evidence
- **THEN** preview retains the incomplete week, leaves winner and ratings absent and lists those gaps

#### Scenario: Repeated offline preview
- **WHEN** the same source hashes, parser version and reviewed mappings are supplied twice
- **THEN** the canonical plan content and digest are identical and no network or database write occurs

### Requirement: Corrections and ambiguous interpretation require review
Corrections SHALL identify exact source records, original values, replacement values and reasons. Uncertain dates, grouping, names, catalog matches or rating phases SHALL remain blocked until explicitly resolved or excluded in the review plan. The approved Singles Night week 7 correction SHALL use January 14, 2026 while retaining the original source label.

#### Scenario: Approved date typo
- **WHEN** the source label says January 14, 2025 and its reviewed correction selects January 14, 2026
- **THEN** the candidate event date is 2026-01-14 and provenance retains the original label and correction

#### Scenario: Ambiguous artist and title
- **WHEN** a message cannot establish which text names the artist and which names the album
- **THEN** the candidate is unresolved and cannot become a catalog record until reviewed

### Requirement: Historical ratings preserve their source meaning
The importer SHALL recognize explicit numeric 1–5 ratings and unambiguous Unicode full/empty/half-star notation, preserving original precision, favorite track, review, authorship and timestamps. Instruction templates, examples and ordinary chat SHALL NOT become ratings. Conflicting numbers, out-of-range values or multiple incompatible ratings for one album-week author SHALL require review.

#### Scenario: Unicode rating with optional fields
- **WHEN** a reviewed album-rating message contains three full stars and one half-star, a favorite track and a review
- **THEN** its candidate stores 3.5 on the 1–5 scale and preserves the supplied optional fields

#### Scenario: Template and contradictory values
- **WHEN** a thread contains a rating tutorial and a reply whose numeric score contradicts its stars
- **THEN** the tutorial produces no rating and the contradictory reply remains unresolved

### Requirement: Attribution respects existing identity and access
Historical authors SHALL be matched by Discord ID through reviewed identity decisions. Names alone MUST NOT establish an existing-account match. Explicitly approved new historical identities SHALL receive no membership, role, provider token or public listening access. Existing handles, linked accounts and privacy settings MUST remain unchanged. Public poll results MUST NOT be converted into private ballots.

#### Scenario: Existing and new participants
- **WHEN** a reviewed plan includes an existing Discord-linked author and an approved new historical author
- **THEN** the former reuses the existing account, the latter has no club membership, and neither account's privacy or credentials change

#### Scenario: Attribution based only on a name
- **WHEN** a Singles Night heading names someone without an unambiguous Discord identity mapping
- **THEN** author attribution remains unresolved rather than attaching the record to a similarly named user

### Requirement: Database application uses the exact checked plan
An operator-only command SHALL check a reviewed plan against the target database without writes, showing proposed inserts, existing matches and conflicts. Apply SHALL require that plan's digest and revalidate sources and target preconditions before one atomic transaction. Normal web/bot write authorization SHALL remain unchanged; there SHALL be no public import endpoint.

#### Scenario: Stale target or edited plan
- **WHEN** a checked plan or one of its target preconditions changes before apply
- **THEN** apply refuses without persisting any part of the import and requests a new target check

#### Scenario: Mid-import failure
- **WHEN** persisting a dependent rating fails after earlier candidates have been processed
- **THEN** no new identities, catalog rows, club records or import-ledger rows from that transaction remain

### Requirement: Provenance prevents duplicate and destructive replays
Imported records SHALL have stable source identities independent of filenames and retain minimal source references, hashes and correction provenance. Reapplying identical reviewed input SHALL create no duplicate records. Changed evidence or collisions with independently created records SHALL be reported as conflicts, never silently overwritten. Deletion of a user's imported activity SHALL not be reversed by replaying the same import.

#### Scenario: Identical retry and expanded export
- **WHEN** an applied export is repeated with different filenames and later expanded with new non-conflicting source records
- **THEN** existing source identities are reused and only the new approved records are inserted

#### Scenario: Edited source or manually edited target
- **WHEN** an already imported source message or its stored target has changed
- **THEN** a subsequent target check reports the conflict and automatic apply refuses to overwrite it

#### Scenario: Account deletion followed by replay
- **WHEN** an imported participant deletes their account and the same source plan is replayed
- **THEN** their dependent imported contributions remain deleted and the replay does not recreate their account or contributions

### Requirement: Historical import has no live delivery or acquisition side effects
Import and verification SHALL create no schedules, outbox events, queued jobs, Discord sends, OAuth credential exchanges, scrobble imports or audio downloads. Source files and full conversations SHALL remain outside Git and public API responses. Automated fixtures SHALL be synthetic and contain no real participant data or credentials.

#### Scenario: Import with past deadlines
- **WHEN** reviewed historical weeks include nomination, poll and discussion dates in the past
- **THEN** only historical records and minimal import provenance are persisted and all delivery/job counts remain unchanged

#### Scenario: Export privacy
- **WHEN** members read imported archive records
- **THEN** responses include approved structured club fields and source links, without local paths, source-file contents or unrelated conversation
