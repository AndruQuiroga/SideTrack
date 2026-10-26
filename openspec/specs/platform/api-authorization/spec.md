# platform/api-authorization Specification

## Purpose
Defines how callers authenticate to the Sidetrack API, how a trusted client acts on behalf of a user, and how the API responds when a request is not allowed.

## Requirements

### Requirement: Every non-public route requires a client credential
Every request SHALL carry `Authorization: Bearer <token>` matching a configured client's token, except `GET /health` and `POST /integrations/lastfm/callback`. This applies to all methods, GET included.

#### Scenario: Anonymous read
- **WHEN** a request to `GET /weeks/` has no bearer token
- **THEN** the API responds 401 with `{"error": "unauthorized"}` and no week data

#### Scenario: Unknown token
- **WHEN** a request to `GET /users/{id}/listening/recent` carries a token that no client holds
- **THEN** the API responds 401

#### Scenario: Public routes stay public
- **WHEN** an anonymous client calls `GET /health`
- **THEN** the API answers it normally, without a 401

### Requirement: Each client has its own credential and fixed scopes
The API SHALL identify the calling client by its token and SHALL allow only the operations in that client's scope set. The web and bot clients SHALL have distinct tokens. The shared `SIDETRACK_API_TOKEN` SHALL NOT grant access.

#### Scenario: Bot calls a web-only operation
- **WHEN** the bot client, acting for a user, calls `GET /users/{that user}/linked-accounts`
- **THEN** the API responds 403 with `{"error": "forbidden"}`

#### Scenario: Retired shared token
- **WHEN** a request carries the value of the old shared `SIDETRACK_API_TOKEN`, and that value is not a client token
- **THEN** the API responds 401

### Requirement: The API fails closed on client configuration
Outside development mode, the API SHALL refuse to start when any configured client lacks a token or when two clients share a token.

#### Scenario: Missing bot token
- **WHEN** the API starts with `SIDETRACK_ENV=production` and no `SIDETRACK_BOT_API_TOKEN`
- **THEN** startup fails with an error naming `SIDETRACK_BOT_API_TOKEN` and not containing any token value

#### Scenario: Duplicate tokens
- **WHEN** the web and bot tokens are the same value
- **THEN** startup fails with an error saying that client tokens must be distinct

### Requirement: Clients act for a user through an explicit header
A client SHALL name the acting user in `X-Sidetrack-Act-As`. The web client may use only `user:<uuid>` and the bot only `discord:<snowflake>`, which resolves through the user's linked Discord account. A request without the header runs as the client alone.

#### Scenario: Web acts for a user
- **WHEN** the web client sends `X-Sidetrack-Act-As: user:U` to `GET /users/U/linked-accounts`
- **THEN** the API answers it as user U

#### Scenario: Bot acts for a Discord user
- **WHEN** the bot client sends `X-Sidetrack-Act-As: discord:D` and D is linked to user U
- **THEN** a nomination created by that request belongs to user U

#### Scenario: Wrong subject form for the client
- **WHEN** the bot client sends `X-Sidetrack-Act-As: user:U`
- **THEN** the API responds 403 and nothing is written

#### Scenario: Unknown subject
- **WHEN** the bot client sends `discord:D` and no user has Discord account D linked
- **THEN** the API responds 403 with `{"error": "unknown_actor"}`

#### Scenario: Malformed header
- **WHEN** a client sends `X-Sidetrack-Act-As: user:not-a-uuid`
- **THEN** the API responds 400

### Requirement: The acting user is taken from the principal, not the request body
For writes made on behalf of a user, the API SHALL record the acting user as the owner. A `user_id` supplied in the body or query that differs from the acting user SHALL be rejected with 403 and nothing written.

#### Scenario: Vote cast for someone else
- **WHEN** the bot acts for user U and posts a vote whose body says `user_id: V`
- **THEN** the API responds 403 and no vote is stored

#### Scenario: Omitted user_id
- **WHEN** the web client acts for user U and posts a nomination with no `user_id`
- **THEN** the nomination is stored for user U

### Requirement: Every route declares an access policy
The API SHALL deny any route that has no declared access policy, and it SHALL NOT start when a registered route other than the public routes has no policy.

#### Scenario: Route without a policy
- **WHEN** the application registers a route that declares no policy
- **THEN** creating the application fails with an error naming that route's method and path

#### Scenario: Policy table covers the API
- **WHEN** the route-policy test enumerates the registered routes
- **THEN** every route matches exactly one entry in the documented policy table

### Requirement: Authorization outcomes are logged without credentials
For each request the API SHALL log the client ID, the acting user ID if there is one, and the outcome, together with the request ID. Logs SHALL NOT contain bearer tokens.

#### Scenario: Denied request
- **WHEN** the bot client is refused with 403
- **THEN** the log line for that request ID contains `client=bot` and the denial reason
- **AND** it does not contain the bot token value

### Requirement: The API does not serve browsers directly
The API SHALL NOT send CORS headers that allow any browser origin to make credentialed requests.

#### Scenario: Browser preflight
- **WHEN** a browser sends an `OPTIONS` preflight from the website's origin
- **THEN** the response has no `Access-Control-Allow-Origin` header for that origin
