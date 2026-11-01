# Spec Delta

## MODIFIED Requirements

### Requirement: Embedding is idempotent and revision-aware
An asset whose embedding for a model already has the current checkpoint revision and pipeline version, and whose window vectors for that model, revision and pipeline are stored, SHALL be skipped. An embedding made with an older revision or pipeline, or a current embedding without its stored window vectors, SHALL be replaced together with its window vectors when that asset is embedded again.

#### Scenario: Job runs twice
- **WHEN** the same embedding job's assets are embedded a second time with no change to the model
- **THEN** the embedding rows are unchanged, and the second result reports those assets as already current

#### Scenario: Revision changed
- **WHEN** an asset's stored embedding has an older checkpoint revision than the enabled model's
- **THEN** the embed command counts it as missing, and embedding it replaces the row with one carrying the current revision

#### Scenario: Current embedding without windows
- **WHEN** an asset has a current pooled embedding but no stored window vectors, and the operator runs the embed command
- **THEN** the command counts the asset as missing, and embedding it stores its window vectors and an equal pooled vector
