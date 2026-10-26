# listening/import-checkpoints Specification

## Purpose
Let Last.fm imports resume after worker restarts without losing their committed
checkpoint or inserting duplicate listens when a job is retried.

## Requirements

### Requirement: Checkpoints advance with committed listens
The system SHALL store a Last.fm checkpoint per user and provider account in Postgres. Successful imports MUST commit checkpoint advancement and listen inserts in one transaction. Failed imports MUST NOT advance it. An explicit since_ts MUST override the starting checkpoint without moving the stored checkpoint backward.

#### Scenario: Worker resumes after restart
- **WHEN** a user imports listens successfully and a later worker imports without since_ts
- **THEN** it resumes from the persisted account checkpoint

#### Scenario: Import fails before commit
- **WHEN** an import fails after processing records but before transaction commit
- **THEN** neither those listens nor checkpoint advancement is persisted

#### Scenario: Explicit historical retry
- **WHEN** an import supplies since_ts older than the saved checkpoint
- **THEN** it uses that timestamp for the fetch and leaves the checkpoint at or above its previous value

### Requirement: Replays and competing imports are safe
Reimporting existing listens SHALL skip duplicates using the existing user, track and played_at uniqueness rule. Concurrent jobs for the same user and Last.fm account MUST serialize their checkpoint updates. Deleting a user MUST remove its checkpoint and prevent a queued import from recreating user data.

#### Scenario: Commit precedes worker failure
- **WHEN** a worker commits listens and dies before acknowledging its job, then recovery replays the payload
- **THEN** the existing listens remain single rows and the retry can complete successfully

#### Scenario: Overlapping imports
- **WHEN** two jobs import overlapping listens for the same account
- **THEN** both finish without uniqueness failures or checkpoint regression

#### Scenario: User deleted before execution
- **WHEN** an import runs after its user was deleted
- **THEN** it terminates with a safe user-unavailable outcome and creates no listens or checkpoints
