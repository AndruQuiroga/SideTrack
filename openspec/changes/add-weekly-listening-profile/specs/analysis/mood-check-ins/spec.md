# Spec Delta

## Purpose

Lets a user record how a week felt and compares that with their listening honestly.

## ADDED Requirements

### Requirement: Users record one check-in per week
A user SHALL submit valence and energy from 1 to 5 for a week; a second submission replaces the first. Others SHALL not read it.

#### Scenario: Replace
- **WHEN** a user checks in twice for one week
- **THEN** one check-in with the latest values exists

#### Scenario: Privacy
- **WHEN** another member requests the check-ins
- **THEN** the response is 403

### Requirement: Correlations show n and uncertainty
The correlation read model SHALL return Spearman rho, n weeks and a 95% bootstrap interval, and SHALL return `not_enough_check_ins` below 8 paired weeks.

#### Scenario: Few check-ins
- **WHEN** 5 weeks have both a profile and a check-in
- **THEN** the result is `not_enough_check_ins` with n 5
