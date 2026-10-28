# Spec Delta

## MODIFIED Requirements

### Requirement: Week deadlines persist with week changes
Creating or updating a non-historical week SHALL transactionally reconcile its nomination reminder, nomination-close, poll-open and ratings-open notifications. Editing a deadline MUST invalidate obsolete pending occurrences. Disabled or missing deadlines and deleted weeks MUST NOT produce future notifications. Historical imported weeks MUST NOT have active notification schedules or deliverable notices, including after edits or restarts.

#### Scenario: Restart before a deadline
- **WHEN** the API, worker and bot restart after saving a week and before its deadline
- **THEN** its current notifications still become due from the saved schedule

#### Scenario: Deadline changes
- **WHEN** a week deadline changes before delivery
- **THEN** no pending notification from the superseded deadline is newly claimed and the replacement occurrence is scheduled once

#### Scenario: Historical deadlines are retained without scheduling
- **WHEN** a historical imported week stores past deadlines and is subsequently edited, reconciled or read after a restart
- **THEN** its dates remain readable but no reminder, close, poll-open or ratings-open notification becomes scheduled, produced or claimable

#### Scenario: Historical week has obsolete delivery state
- **WHEN** a historical week has an existing schedule or pending notice before reconciliation
- **THEN** reconciliation disables the schedule and makes the notice ineligible for delivery without sending a catch-up message
