# Spec Delta

## ADDED Requirements

### Requirement: Share snapshots are the only path outside the owner's visibility
Personal listening data SHALL reach a caller outside the owner's `listening_visibility` only through a published, unexpired, unrevoked share snapshot, and only the snapshot's fields. Publishing or revoking a share SHALL NOT change `listening_visibility`.

#### Scenario: Private user shares a card
- **WHEN** a `private` user publishes a share and a non-member opens its link
- **THEN** the snapshot is returned, `GET /users/{id}/listening/recent` still responds 404 to that non-member, and the user's visibility is still `private`

#### Scenario: Revoked share
- **WHEN** the owner revokes the link
- **THEN** the same caller receives 410 from the link and 404 from every listening route
