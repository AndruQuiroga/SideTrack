# Spec Delta

## Purpose

Defines how external music and chat accounts (Last.fm, Discord, ListenBrainz) are linked to Sidetrack users, and what the API may reveal about those links.

## ADDED Requirements

### Requirement: Linked-account responses never contain credentials
Any API response that describes a linked account SHALL omit access tokens, refresh tokens, session keys and API secrets. It MAY report whether a credential is present and when it expires.

#### Scenario: Listing a user's linked accounts
- **WHEN** a client requests `GET /users/{user_id}/linked-accounts` for a user with a Last.fm account holding a session key
- **THEN** each returned item includes `provider`, `provider_user_id`, `display_name` and `has_credentials: true`
- **AND** no field in the response body contains the session key value

#### Scenario: Creating a linked account
- **WHEN** an authorized client creates a linked account with an `access_token`
- **THEN** the 201 response omits `access_token` and `refresh_token`

### Requirement: Last.fm linking binds to the initiating user
A Last.fm link SHALL attach to the user identified by a server-signed `state` value issued when linking started. The callback SHALL NOT accept a user identifier from the caller.

#### Scenario: Successful link
- **WHEN** an authorized client calls `POST /integrations/lastfm/connect` for user U with a callback URL
- **THEN** the response contains a Last.fm authorization URL whose callback carries a `state` value
- **AND** posting the Last.fm `token` and that `state` to `/integrations/lastfm/callback` links the Last.fm account to user U

#### Scenario: Tampered or foreign state
- **WHEN** the callback receives a `state` whose signature does not verify
- **THEN** the API responds 400 and no linked account is created or changed

#### Scenario: Expired state
- **WHEN** the callback receives a correctly signed `state` older than 15 minutes
- **THEN** the API responds 400 and no linked account is created or changed

#### Scenario: User identifier supplied by the caller
- **WHEN** the callback request includes a `user_id` parameter
- **THEN** the parameter is ignored and the link targets only the user named in `state`

### Requirement: Conflicting links leave existing accounts unchanged
If the Last.fm account is already linked to a different user, the callback SHALL respond 409 and SHALL NOT modify the existing link's stored credentials.

#### Scenario: Account already linked elsewhere
- **WHEN** Last.fm user `alice` is linked to user A and user B completes the Last.fm flow as `alice`
- **THEN** the API responds 409
- **AND** user A's stored Last.fm credential is unchanged

#### Scenario: Re-linking the same user
- **WHEN** user A completes the Last.fm flow again as `alice`
- **THEN** the API responds 200 and user A's stored credential is replaced with the new session key
