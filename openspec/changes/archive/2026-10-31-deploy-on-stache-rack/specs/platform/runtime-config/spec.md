# Spec Delta

## Purpose

Defines where Sidetrack services read configuration and secrets from at runtime, so the same image runs locally and on Stache-Rack without secrets in the image or the repo.

## ADDED Requirements

### Requirement: Settings come from env vars or secret files
The API SHALL read each setting from an environment variable or from a file of the same lowercase name in the secrets directory (default `/run/secrets`). When both exist, the environment variable SHALL take precedence.

#### Scenario: Secret supplied as a Docker secret
- **WHEN** `/run/secrets/sidetrack_api_token` contains `abc` and `SIDETRACK_API_TOKEN` is unset
- **THEN** the API's service token is `abc`

#### Scenario: Env var overrides a secret file
- **WHEN** `/run/secrets/sidetrack_api_token` contains `abc` and `SIDETRACK_API_TOKEN=xyz`
- **THEN** the API's service token is `xyz`

#### Scenario: Secret file with a trailing newline
- **WHEN** a secret file contains `abc\n`
- **THEN** the setting value is `abc`

### Requirement: Secrets never appear in logs or images
Configuration values marked secret SHALL NOT be written to logs, error responses or the startup banner, and SHALL NOT be baked into container images.

#### Scenario: Startup logging
- **WHEN** the API starts with a database URL containing a password
- **THEN** the startup logs show the database host and name but not the password

#### Scenario: Image contents
- **WHEN** a built API or web image is inspected
- **THEN** it contains no `.env` file and no secret values in its environment or layers
