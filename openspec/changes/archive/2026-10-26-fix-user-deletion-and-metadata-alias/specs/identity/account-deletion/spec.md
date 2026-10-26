# Spec Delta

## Purpose

Defines what happens when a user account is deleted: the account and every record the database ties to it are removed in one step, whatever data the user has.

## ADDED Requirements

### Requirement: Deleting a user removes their dependent records
When an authorized `DELETE /users/{user_id}` succeeds, the system SHALL respond 204 and remove the user together with every row the database cascades from it. That covers linked accounts, listen events, import checkpoints, nominations, votes, ratings, follows in both directions, compatibility rows, taste profiles, recommendations and club membership. Deletion MUST NOT fail because the user has dependent rows.

#### Scenario: User with listening history
- **WHEN** a user who has stored listen events and a Last.fm import checkpoint deletes their own account
- **THEN** the response is 204, and the user, their listen events and their checkpoint no longer exist

#### Scenario: User with club activity and social links
- **WHEN** a club member who has a nomination, a vote, a rating, a follower, a followee and a compatibility row deletes their own account
- **THEN** the response is 204, and none of those rows remain

#### Scenario: Other users' data is untouched
- **WHEN** a user is deleted while another user has listen events and ratings in the same weeks
- **THEN** the other user's listen events and ratings are unchanged

### Requirement: Deletion leaves no partial state
Deleting a user SHALL be atomic: either the user and all dependent rows are removed, or nothing is.

#### Scenario: Deletion is refused
- **WHEN** a client calls `DELETE /users/{user_id}` for a user other than the acting user
- **THEN** the response is 404, and the user and all of their rows remain
