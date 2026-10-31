# Spec Delta

## Purpose

Defines how Sidetrack's production database is backed up on a schedule, how each backup is proven usable, how long backups are kept, and where copies live.

## ADDED Requirements

### Requirement: Backups run on a schedule
The system SHALL create a backup of the production database at least once a day without operator action. A backup SHALL appear under its final name only after the dump completes and its checksum is recorded.

#### Scenario: Scheduled run succeeds
- **WHEN** the daily backup runs against a reachable database
- **THEN** a new non-empty dump and a matching SHA-256 checksum file exist in the backup directory

#### Scenario: Dump fails part way
- **WHEN** the dump command exits non-zero
- **THEN** no file with a final backup name is created, temporary output is removed, and the run exits non-zero

#### Scenario: Backup storage is not mounted
- **WHEN** the backup directory is not on its expected dedicated mount
- **THEN** the run exits non-zero and writes nothing to the root disk

### Requirement: Backups are protected from casual reading
Backup files SHALL be readable only by root, because they contain members' data and stored provider tokens. Backup output and logs MUST NOT contain database credentials or heartbeat URLs.

#### Scenario: New backup permissions
- **WHEN** a backup completes
- **THEN** the dump and checksum file are owned by root with no group or other access

#### Scenario: Failure output
- **WHEN** a run fails
- **THEN** its log names the failed step and contains no credential or heartbeat URL

### Requirement: Retention removes only this job's backups
The system SHALL keep the 7 newest daily, 4 newest weekly and 6 newest monthly backups. Retention MUST only consider files that follow the scheduled backup naming pattern, and MUST NOT remove the newest backup that has passed its checksum check.

#### Scenario: Older daily backups expire
- **WHEN** retention runs with more scheduled backups than the policy keeps
- **THEN** only scheduled backups outside the policy are removed

#### Scenario: Manual dumps are preserved
- **WHEN** retention runs and the directory holds a manually named dump
- **THEN** that dump is unchanged, whatever its age

#### Scenario: Every recent backup failed
- **WHEN** no backup has been created inside the daily window
- **THEN** retention removes nothing

### Requirement: Backups are copied to a second host
The system SHALL copy each completed backup and its checksum to storage on a different physical host, and SHALL confirm the checksum at the destination. Retention SHALL apply to the copies by the same policy.

#### Scenario: Copy succeeds
- **WHEN** a backup completes and the second host is reachable
- **THEN** the destination holds the file, and its SHA-256 matches the recorded checksum

#### Scenario: Second host unavailable
- **WHEN** the copy cannot complete
- **THEN** the local backup is kept, the run reports failure, and the next run retries every backup missing from the destination

### Requirement: Restores are proven regularly
At least once a week the system SHALL restore the newest backup into a disposable Postgres 16 + pgvector database with no network access. The check SHALL confirm the checksum, that the schema is at the expected migration head, and that representative tables contain records. It MUST NOT connect to the production database, and the disposable database SHALL be removed afterwards.

#### Scenario: Restore check passes
- **WHEN** the newest backup restores and its schema and record checks pass
- **THEN** the check exits zero and the disposable database is removed

#### Scenario: Corrupt backup
- **WHEN** the newest backup fails its checksum or restore
- **THEN** the check exits non-zero, no heartbeat is sent, and the disposable database is removed

#### Scenario: Empty restored data
- **WHEN** a restored database has no club weeks
- **THEN** the check exits non-zero
