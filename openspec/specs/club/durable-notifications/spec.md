# club/durable-notifications Specification

## Purpose
Preserve club reminder deadlines and pending Discord notifications across API,
worker and bot restarts without keeping the schedule in process memory.

## Requirements

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

### Requirement: Notification production is idempotent
A due occurrence SHALL create at most one outbox event per week, event kind and schedule revision. After downtime, close and phase notices MUST catch up; a one-hour nomination reminder whose closing time has passed MUST be skipped. Initial cutover MUST NOT replay historical closed-week notifications.

#### Scenario: Competing workers
- **WHEN** two workers process the same due occurrence
- **THEN** only one corresponding outbox event exists

#### Scenario: Restart after nominations close
- **WHEN** a saved schedule becomes overdue during downtime spanning nomination close
- **THEN** close and poll-open notices become deliverable once and the obsolete one-hour reminder is skipped

### Requirement: Delivery is leased and acknowledged
The bot SHALL claim due outbox events through service-authenticated API operations with expiring lease tokens. Successful Discord delivery MUST be acknowledged with the matching token and message ID. Expired leases MUST be reclaimable; stale acknowledgments MUST be rejected. Retryable failures MUST preserve pending delivery with bounded backoff, while exhausted or permanent failures remain visible as failed.

#### Scenario: Bot crashes before sending
- **WHEN** the bot claims an event and dies before sending it
- **THEN** another bot can reclaim it after lease expiry

#### Scenario: Delivery acknowledged
- **WHEN** the bot acknowledges a sent message using its current lease token
- **THEN** subsequent claims omit that delivered event

#### Scenario: Unauthorized or stale client
- **WHEN** a client claims without the service token or acknowledges with an expired lease token
- **THEN** the API rejects the operation without changing delivery state

#### Scenario: Discord failure
- **WHEN** sending encounters a retryable failure and later exhausts its retry budget
- **THEN** delivery is retried with backoff up to the limit and then remains visibly failed

### Requirement: Delivery semantics are explicit
Notifications SHALL retain current club reminder meaning and target selection. Delivery MUST be documented as at least once: a crash between sending and acknowledgment can duplicate an external message. Notifications MUST NOT change winners or enforce nomination, voting or rating phases.

#### Scenario: Send succeeds before bot crash
- **WHEN** Discord accepts a message and the bot crashes before acknowledgment
- **THEN** the event remains recoverable and a possible duplicate is documented rather than claiming exactly-once delivery
