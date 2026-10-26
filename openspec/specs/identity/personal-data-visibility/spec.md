# identity/personal-data-visibility Specification

## Purpose
Defines who may see and change a person's own data: profile, linked accounts, listening history, taste profiles, compatibility, recommendations and background jobs.

## Requirements

### Requirement: Listening visibility is private by default
Every user SHALL have a `listening_visibility` of `private` or `club`, defaulting to `private`, and only that user SHALL be able to change it.

#### Scenario: New and migrated users
- **WHEN** a user is created, or already existed before the migration
- **THEN** their `listening_visibility` is `private`

#### Scenario: Changing someone else's setting
- **WHEN** user U patches user V's `listening_visibility`
- **THEN** the API responds 403 and V's setting is unchanged

### Requirement: Linked accounts are visible only to their owner
Linked accounts SHALL be listed, created or removed only by the user they belong to, whatever their visibility setting. Creating users, looking users up by provider ID, and attaching a first Discord account to a user who has none SHALL require the provisioning scope held by the web and bot clients acting as themselves.

#### Scenario: Another member reads linked accounts
- **WHEN** member U requests `GET /users/V/linked-accounts`
- **THEN** the API responds 404

#### Scenario: Provisioning attaches only a first Discord account
- **WHEN** the bot client, acting as itself, links a second Discord account to a user who already has one
- **THEN** the API responds 403 and nothing is linked

#### Scenario: Provider lookup without the provisioning scope
- **WHEN** the web client acting for a user calls `GET /users/lookup/by-provider/discord/{id}`
- **THEN** the API responds 403

### Requirement: Listening data and taste profiles follow the owner's visibility
A user's listen events, recent listening and taste profiles SHALL be readable by that user. Club members SHALL also see them only when the owner's visibility is `club`. Everyone else SHALL get 404.

#### Scenario: Private listening
- **WHEN** member U requests `GET /users/V/listening/recent` and V is `private`
- **THEN** the API responds 404

#### Scenario: Shared with the club
- **WHEN** V is `club`, and club member U requests V's recent listening
- **THEN** V's recent listens are returned

#### Scenario: Unfiltered listen event list
- **WHEN** user U requests `GET /listen-events/` without a `user_id`
- **THEN** only U's own listen events are returned

### Requirement: Only owners write their personal data
Importing listens, triggering Last.fm ingest and recomputing taste profiles SHALL act only on the acting user's own data.

#### Scenario: Ingest for another user
- **WHEN** user U posts `/ingest/lastfm` with `user_id: V`
- **THEN** the API responds 403 and no job is enqueued

### Requirement: Recommendations are visible only to their owner
Recommendations SHALL be returned only for the acting user.

#### Scenario: Someone else's recommendations
- **WHEN** user U requests `GET /recommendations?user_id=V`
- **THEN** the API responds 404

### Requirement: Compatibility needs consent from the other user
A compatibility result SHALL be returned only to one of the two users. Both SHALL be club members, and the other user's visibility SHALL be `club`.

#### Scenario: Other user is private
- **WHEN** member U requests `/users/U/compatibility/V` and V is `private`
- **THEN** the API responds 404

#### Scenario: Third party
- **WHEN** member W requests `/users/U/compatibility/V`
- **THEN** the API responds 404, whatever U's and V's settings are

### Requirement: Job status is visible only to the user who submitted the job
A job's status SHALL be returned only to the acting user who submitted it. Jobs with no recorded submitter SHALL be reported as not found.

#### Scenario: Polling another user's job
- **WHEN** user U polls the status of a job that V submitted
- **THEN** the API responds 404

#### Scenario: Polling one's own job
- **WHEN** user U polls the status of a job U submitted
- **THEN** the job's status is returned
