# Spec Delta

## Purpose

Lets a user privately record how a week felt, export or delete those records, and explore the association with their listening without causal or clinical claims.

## ADDED Requirements

### Requirement: Users record one private check-in per week
A user SHALL be able to submit valence and energy from 1 to 5 for a week; a second submission replaces the first. Check-ins SHALL be readable only by their owner, regardless of `listening_visibility`.

#### Scenario: Replace
- **WHEN** a user checks in twice for one week
- **THEN** one check-in with the latest values exists

#### Scenario: Privacy
- **WHEN** another member requests the check-ins
- **THEN** the response is 403

#### Scenario: Public listening does not expose check-ins
- **WHEN** a user's `listening_visibility` is public and another member reads their profile
- **THEN** no check-in values are included

### Requirement: Check-ins can be exported and deleted
A user SHALL be able to export all their check-ins as a machine-readable file and delete all of them without deleting listening data. Account deletion SHALL remove check-ins.

#### Scenario: Export
- **WHEN** the user requests a check-in export
- **THEN** the response contains every check-in with week and values

#### Scenario: Delete check-ins only
- **WHEN** the user deletes their check-ins
- **THEN** no check-ins remain and their listens and profiles are unchanged

### Requirement: Associations are exploratory and show n
The association read model SHALL return the paired weeks, the same-week Spearman rho and n, and the profile and probe versions. It SHALL NOT return a confidence interval or a causal or clinical statement. Below 8 paired weeks, it SHALL return `not_enough_check_ins`. The 8-week threshold SHALL be labelled a product rule.

#### Scenario: Few check-ins
- **WHEN** 5 weeks have both a qualifying profile and a check-in
- **THEN** the result is `not_enough_check_ins` with n 5

#### Scenario: Enough check-ins
- **WHEN** 12 weeks are paired
- **THEN** the result includes the 12 pairs, rho, n 12 and no interval field

#### Scenario: Constant values
- **WHEN** every paired check-in has the same valence
- **THEN** rho is reported as `undefined_constant_input` rather than a number
