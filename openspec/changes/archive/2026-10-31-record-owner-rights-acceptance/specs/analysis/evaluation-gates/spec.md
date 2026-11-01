# Spec Delta

## MODIFIED Requirements

### Requirement: Evaluation datasets have a rights register
Every dataset an evaluation record cites SHALL appear in `docs/evaluations/datasets.yaml` with its source, intended use, recorded terms for audio and for annotations, known gaps, acquisition method, storage location and review date. A record citing a dataset that is missing, or whose entry is `rights_unconfirmed` for that use, SHALL NOT be approved.

#### Scenario: Unregistered dataset
- **WHEN** a record cites `pmemo` and the rights register has no `pmemo` entry
- **THEN** the register check reports the record `incomplete` naming `pmemo`

#### Scenario: Rights unconfirmed
- **WHEN** the register marks MusAV's previews `rights_unconfirmed` and an approved entry cites MusAV audio
- **THEN** the check exits non-zero naming MusAV and the claim

#### Scenario: Owner accepts unconfirmed terms
- **WHEN** the register marks a dataset's audio `owner_accepted` with a date, an acceptor and a scope, and an approved entry cites that audio
- **THEN** the register check reports no rights error for that entry

#### Scenario: Acceptance without a scope
- **WHEN** the register marks a dataset `owner_accepted` with no acceptance scope
- **THEN** the register check fails naming the dataset and `acceptance`
