# Spec Delta

## Purpose

Compares how two consenting listeners' music sounds, side by side, with each side's coverage. Consent is revocable and no verdict is given about either person.

## ADDED Requirements

### Requirement: Both users must opt in
A comparison SHALL be computed and shown only when both users have opted in. Otherwise the route SHALL report `not_opted_in` and SHALL NOT reveal which side declined.

#### Scenario: One side opted out
- **WHEN** user B has not opted in
- **THEN** the response reports `not_opted_in` and contains no comparison data

### Requirement: Results report each side's basis
A result SHALL give both users' eligible track counts, embedded track counts, the model revision and the theme-build version. It SHALL be `not_enough_listening` when either side has fewer than 50 embedded eligible tracks; the threshold is labelled a product rule.

#### Scenario: Small library
- **WHEN** user B has 30 embedded eligible tracks
- **THEN** the result is `not_enough_listening` with both counts

#### Scenario: Coverage shown
- **WHEN** both users qualify
- **THEN** the result includes each side's tracks with audio out of total eligible tracks

### Requirement: No verdict labels or single percentage
A result SHALL present shared sound-worlds, distinct examples per side and method details. It SHALL NOT include a single compatibility percentage or an unvalidated qualitative label such as low, moderate or high.

#### Scenario: Result shape
- **WHEN** a comparison is returned
- **THEN** it has shared and distinct sections, and no headline percentage or low/moderate/high label field

### Requirement: Bridge candidates come from both libraries
Bridge candidates SHALL be up to five tracks from either library, ranked by their minimum similarity to the two users' eligible tracks. Each candidate SHALL name the library it comes from. A user SHALL be able to nominate or dismiss a candidate.

#### Scenario: Bridge list
- **WHEN** both users qualify
- **THEN** up to 5 bridge candidates are returned, each labelled with its source library

### Requirement: Withdrawal removes derived data
When either user withdraws consent or is deleted, every comparison, bridge candidate and nomination involving them SHALL be deleted. The other user SHALL see `not_opted_in` thereafter.

#### Scenario: Withdraw
- **WHEN** user A withdraws consent
- **THEN** no comparison rows involving A remain and user B's next request returns `not_opted_in`
