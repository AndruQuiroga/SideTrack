# platform/schema-migrations Specification

## Purpose
Guarantees that Sidetrack's Alembic migrations build exactly the schema its application code expects, verified on the same database engine production runs.

## Requirements

### Requirement: Migrations build the schema the models describe
Upgrading an empty database to the latest migration SHALL produce a schema with no differences from the SQLAlchemy models, as reported by Alembic's autogenerate comparison.

#### Scenario: Model changed without a migration
- **WHEN** a column is added to a model without a matching migration
- **THEN** the migration test fails and names the table and column

#### Scenario: Models and migrations agree
- **WHEN** the test suite migrates an empty database to head
- **THEN** the comparison reports no differences

### Requirement: Tests run on the production database engine
The API test suite SHALL run against PostgreSQL 16 with pgvector and SHALL NOT fall back to another database engine.

#### Scenario: CI run
- **WHEN** the `python` CI job runs the tests
- **THEN** they use a `pgvector/pgvector:pg16` database built by `alembic upgrade head`

#### Scenario: No database available locally
- **WHEN** neither `SIDETRACK_TEST_DATABASE_URL` nor Docker is available
- **THEN** the test session fails with a message saying how to provide a database, instead of silently using SQLite
