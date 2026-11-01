# Spec Delta

## Purpose

Propose candidate related versions of audio assets (near-identical copies, previews, edits, remixes and covers) with recorded evidence, for the operator to confirm or reject. Candidates are proposals only: they never merge tracks, assets or listens, and "sounds similar" scores never create them.

## ADDED Requirements

### Requirement: Assets have local fingerprints with explicit states
The system SHALL compute a raw Chromaprint fingerprint for each audio asset locally, without contacting any remote service, and store it with the fingerprint method version and analyzed duration. An asset's fingerprint state SHALL be `available`, `failed` with the error, or `unavailable` with a reason when `fpcalc` is missing. A missing fingerprint SHALL NOT be treated as "no match".

#### Scenario: Fingerprint stored
- **WHEN** the fingerprint command runs on an asset with a decodable file
- **THEN** the asset has an `available` fingerprint with the Chromaprint version and analyzed duration, and no network request is made

#### Scenario: fpcalc missing
- **WHEN** the fingerprint command runs in an environment without `fpcalc`
- **THEN** every pending asset reports `unavailable` with reason "fpcalc not installed", and the command exits non-zero

#### Scenario: Coverage reported
- **WHEN** the operator runs the coverage report
- **THEN** it lists counts of `available`, `failed`, `unavailable` and not-yet-fingerprinted assets separately

### Requirement: Near-identical candidates carry evidence
The system SHALL propose a `near_identical` candidate for a pair of assets whose fingerprints align above the method's threshold, recording the method version, score, offset into each asset, matched duration and each asset's preview/full kind. A pair SHALL be proposed at most once per method version.

#### Scenario: Preview inside full track
- **WHEN** a 30-second preview's fingerprint aligns with a full asset of the same recording starting 45 seconds in
- **THEN** a `near_identical` candidate records the score, an offset of about 45 seconds in the full asset, about 30 seconds matched, and that one side is a preview

#### Scenario: Unrelated audio
- **WHEN** two assets of different songs are compared
- **THEN** no candidate is proposed for that pair

#### Scenario: Recomputation does not duplicate
- **WHEN** candidate generation runs twice with the same method version
- **THEN** each pair appears once

### Requirement: Candidates are proposals, never merges
A candidate or a confirmed relation SHALL NOT merge, delete or re-point tracks, assets, listens or listen-to-audio links, and SHALL NOT change any stat, neighbour list or embedding. Candidates SHALL be described as possible related versions, never as the same recording, until the operator confirms that relation.

#### Scenario: Confirmation changes nothing else
- **WHEN** the operator confirms a candidate as `same_recording`
- **THEN** the tracks, assets, listen-to-audio links and embeddings tables are unchanged apart from the relation record

#### Scenario: Candidate wording
- **WHEN** the operator lists unreviewed candidates
- **THEN** each is shown as a possible related version with its method and evidence, and none is labelled the same recording

### Requirement: Sonic similarity never creates candidates
Candidate generation SHALL use only fingerprint alignment and learned version-retrieval methods that passed the version gate. Scores from MuQ-MuLan pooled similarity, mood, themes, facets or any other "sounds similar" measure SHALL NOT create, rank or confirm a candidate.

#### Scenario: Close neighbours are not candidates
- **WHEN** two assets are each other's nearest MuQ-MuLan neighbours but their fingerprints do not align and no gated learned method proposes them
- **THEN** no candidate exists for the pair

### Requirement: The operator confirms or rejects candidates
The operator SHALL be able to confirm a candidate with one relation (`same_recording`, `preview_of`, `edit_of`, `remix_of`, `cover_of`) or reject it, and later revert either decision. Each decision SHALL record who decided, when and the candidate's evidence at that time. A rejected pair SHALL NOT be re-proposed by the same method version.

#### Scenario: Confirm with relation
- **WHEN** the operator confirms a candidate between a radio edit and the album version as `edit_of`
- **THEN** the relation is stored with the operator, timestamp and the candidate's method, version and score

#### Scenario: Rejected pair stays rejected
- **WHEN** the operator rejects a candidate and candidate generation runs again with the same method version
- **THEN** the pair is not proposed again

#### Scenario: Decision reverted
- **WHEN** the operator reverts a confirmation
- **THEN** the relation is removed and the candidate returns to unreviewed

#### Scenario: Asset deleted
- **WHEN** an asset in a candidate or relation is deleted
- **THEN** its candidates and relations are deleted with it

### Requirement: Learned version methods are gated
A learned version-retrieval method SHALL produce `possible_version` candidates only after it has a recorded audio-lab version run, a license and dependency record, the owner's recorded decision and an accepted ADR. Without all four, the `possible_version` kind SHALL report `unavailable` with the missing item, and SHALL NOT be computed from a substitute method.

#### Scenario: No gated method
- **WHEN** the operator requests `possible_version` candidates and no learned method has passed the gate
- **THEN** the command reports `possible_version` as `unavailable` naming the missing gate items, and proposes nothing

#### Scenario: Gated method candidate
- **WHEN** a gated learned method scores a cover pair above its recorded threshold
- **THEN** a `possible_version` candidate records the method, version, score and threshold, and is unreviewed

### Requirement: Candidates are not exposed over HTTP
No HTTP route SHALL return fingerprints, candidates or relations in this capability.

#### Scenario: Route table
- **WHEN** the API's registered routes are listed
- **THEN** none returns fingerprint, candidate or version-relation data
