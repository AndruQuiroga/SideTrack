# Spec Delta

## Purpose

Defines how a club member's rating of a week's album is stored and read back, so ratings and their summaries reflect what members actually submitted.

## ADDED Requirements

### Requirement: Rating submission is stored
An authorized `POST /weeks/{week_id}/ratings` SHALL respond 201 with the stored rating and persist every submitted field: album, nomination, value, favorite track, review and `metadata`. The rating's owner is the acting user. Omitting `metadata` SHALL store and return `null`.

#### Scenario: Member rates with metadata
- **WHEN** a club member submits a rating for a week with value 4.5, a review and `metadata` `{"listened_on": "vinyl"}`
- **THEN** the response is 201, the body contains those values with `metadata` `{"listened_on": "vinyl"}` and `user_id` equal to the member, and the stored row has the same values

#### Scenario: Member rates without metadata
- **WHEN** a club member submits a rating with no `metadata` field
- **THEN** the response is 201 and the body's `metadata` is `null`

#### Scenario: Second rating for the same week
- **WHEN** a member who already rated a week submits another rating for it
- **THEN** the response is 409 and the first rating is unchanged

### Requirement: Stored ratings are readable
`GET /ratings` and `GET /ratings/{rating_id}` SHALL return stored ratings, including their `metadata`, to callers allowed to read club data. The public field name SHALL remain `metadata`.

#### Scenario: Reading a rating back
- **WHEN** a member fetches `GET /ratings/{id}` for a stored rating whose metadata is `{"listened_on": "vinyl"}`
- **THEN** the response is 200 and its `metadata` is `{"listened_on": "vinyl"}`

#### Scenario: Listing a week's ratings
- **WHEN** a member lists `GET /ratings?week_id={id}` for a week with two stored ratings
- **THEN** the response is 200 with both ratings
