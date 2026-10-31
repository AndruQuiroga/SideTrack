# Spec Delta

## ADDED Requirements

### Requirement: Existing assets are imported from a manifest
The import command SHALL create asset records from a manifest for files already present in the configured audio directory, without fetching or making network requests. It SHALL only run when an operator invokes it. Without an explicit apply option it MUST write nothing and SHALL report what would happen. A row SHALL be accepted only when its file exists and the file's SHA-256 matches both the row's hash and the file name.

#### Scenario: Check makes no changes
- **WHEN** the operator runs the import without the apply option
- **THEN** the command reports counts of new, existing and rejected rows, and no database row changes

#### Scenario: Apply creates assets
- **WHEN** the operator applies a manifest whose files all verify
- **THEN** one asset row exists per manifest row, with its source, kind, duration, verification state, artist and title preserved

#### Scenario: File is missing
- **WHEN** a manifest row's file is not in the audio directory
- **THEN** that row is rejected with a reason and no row is created for it

#### Scenario: File does not match its hash
- **WHEN** a file's computed SHA-256 differs from the manifest
- **THEN** that row is rejected with a reason and the file is left unchanged

#### Scenario: Nothing schedules an import
- **WHEN** the worker's registered tasks and persisted schedules are listed
- **THEN** none of them imports a manifest

### Requirement: Manifest import is repeatable and all-or-nothing
Applying the same manifest again SHALL add nothing. A row whose hash already exists, with matching source details, SHALL count as existing. A row that conflicts with an existing asset, or a run with any rejected row, MUST write nothing unless the operator explicitly chooses to skip rejected rows. Conflicts SHALL never be skipped.

#### Scenario: Identical retry
- **WHEN** a manifest that was applied is applied again
- **THEN** no row is added or changed and every row is reported as existing

#### Scenario: Rejected row blocks apply
- **WHEN** the operator applies a manifest with a rejected row and no skip option
- **THEN** the command exits non-zero and writes no rows

#### Scenario: Skipping rejected rows
- **WHEN** the operator applies with the skip option
- **THEN** valid rows are created, and rejected rows are listed with reasons

#### Scenario: Conflicting source
- **WHEN** a row's source and source reference belong to an existing asset with a different hash
- **THEN** the command exits non-zero and writes no rows, even with the skip option

### Requirement: Imports don't carry database-specific or mismatched records
The import SHALL NOT copy catalog track links from the manifest, because they belong to another database. Rows whose verification state is `mismatch` SHALL be rejected, because they are known not to be the claimed track. Manifest rows MUST NOT be logged with credentials or absolute local paths.

#### Scenario: Manifest has a track link
- **WHEN** a row names a `track_id`
- **THEN** the created asset has no track link

#### Scenario: Mismatched asset
- **WHEN** a row's verification state is `mismatch`
- **THEN** that row is rejected with a reason

#### Scenario: Imported assets can be embedded
- **WHEN** the embed command runs after an apply
- **THEN** imported assets with files are queued like fetched assets
