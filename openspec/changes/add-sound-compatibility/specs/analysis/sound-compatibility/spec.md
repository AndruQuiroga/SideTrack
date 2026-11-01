# Spec Delta

## Purpose

Measures how close two consenting listeners' music sounds, with the data each side rests on.

## ADDED Requirements

### Requirement: Both users must opt in
Compatibility SHALL be computed only when both users opted in; otherwise the route SHALL report `not_opted_in`.

#### Scenario: One side opted out
- **WHEN** user B has not opted in
- **THEN** the response reports `not_opted_in` and no score

### Requirement: Scores report their basis
The result SHALL give the overlap score, both users' embedded track counts and the model revision, and SHALL be `not_enough_listening` when either side has fewer than 50 embedded tracks.

#### Scenario: Small library
- **WHEN** user B has 30 embedded tracks
- **THEN** the result is `not_enough_listening`

### Requirement: Bridge songs come from both libraries
Bridge songs SHALL be tracks from either library ranked by their minimum similarity to the two users' distributions.

#### Scenario: Bridge list
- **WHEN** both users qualify
- **THEN** up to 5 bridge tracks are returned, each from one of their libraries

### Requirement: Leaving deletes results
When either user withdraws or is deleted, their compatibility rows SHALL be deleted.

#### Scenario: Withdraw
- **WHEN** user A withdraws consent
- **THEN** no compatibility rows involving A remain
