# Spec Delta

## Purpose

Defines how the Sidetrack website gates pages behind sign-in and keeps API credentials and acting-user claims on the server.

## ADDED Requirements

### Requirement: The browser never talks to the API directly
Website pages and components SHALL fetch API data only through server-side code. No API credential and no API base URL that is meant for credentialed calls SHALL be sent to the browser.

#### Scenario: Built client bundle
- **WHEN** the website is built
- **THEN** no client-side bundle contains the web API token, the `X-Sidetrack-Act-As` header name or a direct call to the API base URL

### Requirement: The acting user always comes from the server session
When the website calls the API for a person, it SHALL send `X-Sidetrack-Act-As: user:<id>`, with the ID taken from the server-side session. It SHALL NOT take that ID from the URL, a form or the request body.

#### Scenario: User ID in the URL
- **WHEN** a signed-in user U opens a website route that accepts a user ID in its path, giving V's ID
- **THEN** the website's API call names U as the acting user, never V

### Requirement: Anonymous visitors are asked to sign in
A page that needs API data SHALL show a sign-in prompt to anonymous visitors, and SHALL NOT call the API on their behalf.

#### Scenario: Anonymous club archive
- **WHEN** a visitor who is not signed in opens `/club`
- **THEN** the page shows a sign-in prompt and lists no weeks

### Requirement: Access denials are shown as such
When the API refuses a request with 403 or `not_a_club_member`, the page SHALL say that the signed-in user lacks access. It SHALL NOT show this as an outage, and SHALL NOT show substitute data.

#### Scenario: Signed-in non-member opens the club
- **WHEN** a signed-in user who is not a club member opens `/club`
- **THEN** the page says that the club archive is for club members, and lists no weeks
