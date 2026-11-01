# Spec Delta

## Purpose

Delivers an opt-in weekly summary card by Discord direct message and records the owner's private reaction check-ins.

## ADDED Requirements

### Requirement: Cards are opt-in, private and durable
A card SHALL be sent only to users who opted in, by direct message, through the notification outbox, at most once per user and week. A card SHALL NOT be posted to a shared channel. Opting out SHALL stop future cards.

#### Scenario: Opted out
- **WHEN** a user has not opted in
- **THEN** no card is queued for them

#### Scenario: DMs blocked
- **WHEN** Discord rejects the direct message
- **THEN** the outbox records the failure reason and no channel message is posted instead

### Requirement: Cards show coverage
A card SHALL state the week, included plays, plays with audio and the timezone. A week that is `not_enough_listening` SHALL say so instead of showing values.

#### Scenario: Thin week card
- **WHEN** the user's week is `not_enough_listening`
- **THEN** the card states that there was not enough listening and shows the counts only

### Requirement: Reactions record private check-ins
A reaction by the card's recipient on the DM card SHALL store that user's check-in for the card's week.

#### Scenario: Reaction
- **WHEN** the recipient reacts 2 on valence
- **THEN** their check-in for that week has valence 2
