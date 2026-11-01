# Spec Delta

## Purpose

Delivers an opt-in weekly summary card in Discord and records reaction check-ins.

## ADDED Requirements

### Requirement: Cards are opt-in and durable
A card SHALL be sent only to users who opted in, through the notification outbox, at most once per user and week.

#### Scenario: Opted out
- **WHEN** a user has not opted in
- **THEN** no card is queued for them

### Requirement: Reactions record check-ins
A reaction on the card SHALL store that user's check-in for the card's week.

#### Scenario: Reaction
- **WHEN** the user reacts 2 on valence
- **THEN** their check-in for that week has valence 2
