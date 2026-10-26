# club/membership-access Specification

## Purpose
Defines who belongs to the album club, which roles they hold, and who may read or change weeks, nominations, ballots, ratings and club notifications.

## Requirements

### Requirement: Club membership is maintained by the bot
Club membership and roles (`member` or `admin`) SHALL be changed only by the bot client acting as itself, or by the operator's admin command. Signing in to the website SHALL NOT create membership.

#### Scenario: Bot records a member
- **WHEN** the bot upserts Discord user D with role `admin`
- **THEN** the user linked to D becomes a club member with role `admin`

#### Scenario: Web cannot grant membership
- **WHEN** the web client, acting for user U, tries to change any membership
- **THEN** the API responds 403 and membership is unchanged

#### Scenario: Member leaves the guild
- **WHEN** the bot marks Discord user D as having left
- **THEN** the user linked to D is no longer a club member, and their past nominations and ratings remain stored

#### Scenario: First admin
- **WHEN** the operator runs the admin-grant command for an existing user
- **THEN** that user becomes a member with role `admin`, without any API credential being involved

### Requirement: Existing participants become members at migration
The migration SHALL make a user a club member with role `member` if they have a linked Discord account and at least one nomination, vote or rating. It SHALL NOT create memberships for other users.

#### Scenario: Seeding
- **WHEN** the migration runs on a database where user A has a Discord account and a rating, and user B has a Discord account and no club activity
- **THEN** A is a member and B is not

### Requirement: Club data is visible to members only
Weeks, nominations, ratings, rating summaries and trending SHALL be readable only by club members, or by the bot client acting as itself. Others SHALL get 403 with `{"error": "not_a_club_member"}`.

#### Scenario: Member reads a week
- **WHEN** a member reads `GET /weeks/{id}`
- **THEN** the week and its nominations are returned

#### Scenario: Signed-in non-member
- **WHEN** a user who is not a member reads `GET /weeks/`
- **THEN** the API responds 403 with `not_a_club_member`

### Requirement: Ballots are private to the voter
A vote SHALL be readable only by the user who cast it. Listing votes SHALL return only the acting user's own votes, and no client acting as itself SHALL read individual ballots.

#### Scenario: Listing votes
- **WHEN** members U and V have both voted and U lists `GET /votes`
- **THEN** only U's votes are returned

#### Scenario: Reading another ballot
- **WHEN** U requests `GET /votes/{id}` for V's vote
- **THEN** the API responds 404

### Requirement: Members participate only as themselves
Only club members SHALL nominate, vote and rate, and always as themselves. A nomination SHALL be edited or withdrawn only by its nominator or by an admin.

#### Scenario: Non-member nominates
- **WHEN** a non-member posts to `/weeks/{id}/nominations`
- **THEN** the API responds 403 and nothing is stored

#### Scenario: Editing someone else's nomination
- **WHEN** member U, who is not an admin, sends `PATCH /nominations/{id}` for V's nomination
- **THEN** the API responds 403 and the nomination is unchanged

#### Scenario: Admin withdraws a nomination
- **WHEN** an admin deletes another member's nomination
- **THEN** the nomination is removed

### Requirement: Week management and moderation require the admin role
Creating weeks, changing week fields other than thread IDs, overriding winners, deleting ratings and editing albums SHALL require an acting user with role `admin`. The bot client acting as itself SHALL be allowed to set only a week's thread ID fields.

#### Scenario: Member creates a week
- **WHEN** a member who is not an admin posts to `/weeks/`
- **THEN** the API responds 403

#### Scenario: Admin overrides a winner
- **WHEN** an admin posts to `/admin/weeks/{id}/override-winner`
- **THEN** the winner is changed

#### Scenario: Bot sets a thread ID
- **WHEN** the bot, acting as itself, patches `nominations_thread_id` on a week
- **THEN** the field is updated

#### Scenario: Bot changes a deadline without an actor
- **WHEN** the bot, acting as itself, patches `poll_close_at`
- **THEN** the API responds 403 and the week is unchanged

### Requirement: Club notifications are delivered only by the bot
The notification claim, ack and fail operations SHALL be available only to the bot client acting as itself.

#### Scenario: Web claims notifications
- **WHEN** the web client calls `POST /club/notifications/claim`
- **THEN** the API responds 403 and no notification is leased
