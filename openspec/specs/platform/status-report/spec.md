# platform/status-report Specification

## Purpose
Keeps the project's record of what actually works generated, evidence-backed and checked in CI, so humans and coding agents can trust it over any other prose.

## Requirements

### Requirement: The status page is generated
`docs/STATUS.md` SHALL be produced by `scripts/gen_status.py` from `docs/status.yaml` and from facts read from the repository, and SHALL say so at the top.

#### Scenario: Regenerating
- **WHEN** `python scripts/gen_status.py` runs
- **THEN** `docs/STATUS.md` contains every capability in `docs/status.yaml`, the API routes, the latest migration revision, the current specs and each in-flight change with its completed and total task counts

#### Scenario: Deterministic output
- **WHEN** the generator runs twice without any repository change
- **THEN** both outputs are byte-identical

### Requirement: Claims need evidence
A capability marked `works` SHALL list at least one evidence path, and every listed evidence path SHALL exist in the repository. Statuses SHALL be one of works, partial, broken, stub or absent.

#### Scenario: Works without evidence
- **WHEN** a capability is marked `works` with no evidence
- **THEN** the generator reports an error naming that capability and exits non-zero

#### Scenario: Missing evidence file
- **WHEN** an evidence path doesn't exist
- **THEN** the generator reports an error naming the path

#### Scenario: Unknown status
- **WHEN** a capability's status is not one of the five allowed values
- **THEN** the generator reports an error naming the capability and value

### Requirement: CI rejects a stale status page
`python scripts/gen_status.py --check` SHALL exit non-zero when `docs/STATUS.md` differs from what the generator would write, and CI SHALL run it.

#### Scenario: Hand edit
- **WHEN** someone edits `docs/STATUS.md` directly, or changes `docs/status.yaml` or the facts it reads without regenerating
- **THEN** `--check` fails with a message telling them to run the generator
