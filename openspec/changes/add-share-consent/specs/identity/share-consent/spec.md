# Spec Delta

## Purpose

Lets a listener share a frozen, previewed snapshot of their own listening through an opt-in, expiring and revocable link, with check-ins and other members' data kept out and each card stating its basis.

## ADDED Requirements

### Requirement: Shares are built from an allow-list of the owner's items
A share SHALL be built only from items the owner selects from an allow-list: `top_tracks`, `sample_and_coverage`, `listening_clock`, `theme_estimates`, `mood_estimates` and `check_in`. No item SHALL be selected by default except `top_tracks` and `sample_and_coverage`. An item whose source is not implemented or not ready SHALL be reported `item_unavailable` and SHALL NOT be included.

#### Scenario: Default selection
- **WHEN** the owner opens a new share for a week
- **THEN** only `top_tracks` and `sample_and_coverage` are selected

#### Scenario: Unimplemented item
- **WHEN** the owner selects `listening_clock` before its source capability exists
- **THEN** the preview reports `listening_clock: item_unavailable` and the snapshot omits it

### Requirement: A preview is a frozen snapshot
Creating a preview SHALL store a snapshot of exactly the values to be shared, owned by the user, unpublished, and SHALL return it. A link SHALL be created only from a previewed snapshot, and the shared page SHALL serve that snapshot unchanged even if the underlying data later changes.

#### Scenario: Data changes after sharing
- **WHEN** a snapshot shows 84 included plays and the owner later overrides a session so the week has 98
- **THEN** the shared page still shows 84

#### Scenario: Link without preview
- **WHEN** a client asks to publish a share without a snapshot ID
- **THEN** the API responds 422 and no link is created

### Requirement: Check-ins need a second explicit confirmation
The `check_in` item SHALL be excluded unless the owner selects it and separately confirms with `confirm_check_in: true` on publish. Without both, the snapshot SHALL contain no check-in field. Check-ins of other users SHALL never be included.

#### Scenario: Selected without confirmation
- **WHEN** the owner selects `check_in` and publishes without `confirm_check_in`
- **THEN** the API responds 422 and no link is created

#### Scenario: Default share
- **WHEN** the owner publishes with default selection
- **THEN** the snapshot contains no check-in field

### Requirement: Another member's data is never shared
A share SHALL contain data about the owner only. Compatibility, blend, comparison or any field derived from another user's listening SHALL be rejected with 422, whatever either user's settings are.

#### Scenario: Compatibility item
- **WHEN** the owner requests a share including a compatibility result with member V
- **THEN** the API responds 422 and no snapshot is created

### Requirement: Cards state units, ranking source and basis
Each snapshot SHALL include the period and timezone, the unit of every number, the ranking source of every ranked list, the included-play sample, the audio coverage of any audio-derived item, and the gate status of any estimate. Theme and mood items SHALL be offered only when their gate is `approved`; mood values SHALL be raw scores or the owner's own percentiles.

#### Scenario: Top tracks basis
- **WHEN** a snapshot includes top tracks for a week
- **THEN** it states "ranked by your included plays", the period, the timezone and the included-play count

#### Scenario: Gate pending estimate
- **WHEN** the owner selects `mood_estimates` while the mood gate is `gate_pending`
- **THEN** the item is reported `item_unavailable` with reason `gate_pending` and omitted

### Requirement: Cards carry no personality or diagnostic claims
Snapshot text SHALL contain only titles, artists, counts, dates, units, sources and fixed labels. It SHALL NOT contain personality, feeling, mental-health, compatibility-percentage or diagnostic statements, and SHALL NOT contain generated prose.

#### Scenario: Guard
- **WHEN** a snapshot is generated from any combination of allowed items
- **THEN** a guard test finds none of the prohibited claim terms in its text fields

### Requirement: Links are unguessable, expiring and revocable
A published link SHALL use a random token of at least 128 bits, stored only as a hash. It SHALL expire after 30 days by default and at most 365. The owner SHALL be able to list and revoke their links; a revoked or expired link SHALL return 410 with no snapshot data, and revoking SHALL delete the snapshot.

#### Scenario: Revoke
- **WHEN** the owner revokes a link and someone then opens it
- **THEN** the response is 410 with no listening data, and the snapshot row no longer exists

#### Scenario: Expiry cap
- **WHEN** the owner requests a 400-day expiry
- **THEN** the API responds 422

#### Scenario: Token not stored
- **WHEN** the share tables are inspected
- **THEN** they contain the token hash and not the token

### Requirement: Shared pages expose no audio and no identity by default
A shared snapshot SHALL NOT contain audio, previews, stream URLs, file paths, cover-art files, user IDs, linked-account names or the owner's display name unless the owner selected `show_display_name`. Opening a link SHALL record only an open count, never viewer identity.

#### Scenario: Default identity
- **WHEN** a link is opened without `show_display_name` selected
- **THEN** the response contains no display name, user ID, linked-account name or audio field

### Requirement: Account deletion revokes shares
Deleting an account SHALL delete all of its snapshots and links; opening any of its links afterwards SHALL return 410.

#### Scenario: Deleted owner
- **WHEN** an owner with two active links deletes their account
- **THEN** both links return 410 and no snapshot rows remain for that user
