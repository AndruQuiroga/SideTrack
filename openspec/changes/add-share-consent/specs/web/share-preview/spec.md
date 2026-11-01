# Spec Delta

## Purpose

Gives a listener a share builder that previews exactly what will leave their account, explains where it goes and what can be revoked, and manages their links; and renders the public card page from the frozen snapshot only.

## ADDED Requirements

### Requirement: The builder previews exactly what will be shared
The share builder SHALL list the allow-listed items with their default selection, show unavailable items with their reason, and before publishing SHALL render the API's snapshot exactly as the public page will. The Share control SHALL be disabled until a preview has been generated for the current selection.

#### Scenario: Selection changed after preview
- **WHEN** the owner previews, then ticks `listening_clock`
- **THEN** the Share control is disabled until a new preview is generated

#### Scenario: Unavailable item
- **WHEN** the API reports `theme_estimates: item_unavailable` with reason `gate_pending`
- **THEN** the item is shown unticked and disabled with "not available: not yet validated"

### Requirement: Check-ins require a separate confirmation
Ticking the check-in item SHALL show a separate confirmation stating that private check-in answers will be visible to anyone with the link, and publishing SHALL send `confirm_check_in: true` only after the owner accepts it. Another member's data SHALL NOT be offered.

#### Scenario: Decline confirmation
- **WHEN** the owner ticks check-in and declines the confirmation
- **THEN** the item is unticked and the preview contains no check-in

### Requirement: Destination and retraction limits are explained
Before publishing, the builder SHALL state that anyone with the link can open it, that it is not indexed, its expiry date, that it can be revoked, and that revoking cannot retract screenshots or downloaded images.

#### Scenario: Explanation shown
- **WHEN** the owner reaches the Share step
- **THEN** all five statements are visible next to the Share control

### Requirement: Owners manage their links
Settings SHALL list the owner's links with creation date, expiry, items included and open count, and let the owner revoke each. After a revoke succeeds, the list SHALL be refreshed from the API; if it fails, the link SHALL still be shown as active with an error.

#### Scenario: Revoke from settings
- **WHEN** the owner revokes a link and the API confirms
- **THEN** the link is shown as revoked in the refreshed list

#### Scenario: Revoke fails
- **WHEN** the revoke request fails
- **THEN** the link remains shown as active and an error is displayed

### Requirement: The public card renders the snapshot only
`/share/{token}` SHALL render only the snapshot's fields with their units, ranking source, period, timezone, sample and coverage, SHALL send `noindex`, SHALL play or embed no audio, and SHALL show "this link is no longer available" with no data on 410 and "unavailable" on other errors.

#### Scenario: Revoked link
- **WHEN** a visitor opens a revoked link
- **THEN** the page reads "this link is no longer available" and shows no listening data

#### Scenario: Valid link
- **WHEN** a visitor opens a valid link
- **THEN** the page shows the snapshot's tracks with "ranked by your included plays", the period and the sample size, a `noindex` robots directive, and no audio element

### Requirement: Builder and settings are owner-only
The share builder and link list SHALL be shown only to the signed-in owner; signed-out visitors SHALL get a sign-in prompt preserving the path. The public card page SHALL NOT require sign-in.

#### Scenario: Signed out builder
- **WHEN** a signed-out visitor opens the share builder
- **THEN** they are prompted to sign in and returned to the builder afterwards
