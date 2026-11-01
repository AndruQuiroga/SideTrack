# Spec Delta

## Purpose

Stores text-tower vectors for vocabulary terms in the same joint space as audio embeddings, so audio can be compared with words under recorded provenance.

## ADDED Requirements

### Requirement: Vocabulary vectors carry provenance
Each stored text vector SHALL record its term, prompt template, vocabulary version, model, revision and dimension. It SHALL be compared only with audio vectors of the same model and revision.

#### Scenario: Embedding the vocabulary
- **WHEN** the operator embeds vocabulary v1 with MuQ-MuLan
- **THEN** one vector per term and prompt template exists with the model revision

#### Scenario: Revision mismatch
- **WHEN** a comparison is requested between text vectors and audio vectors of different revisions
- **THEN** it is refused with `revision_mismatch`

### Requirement: Text embedding is unavailable without the model
When the text tower cannot load, the job SHALL fail with `unavailable` and store nothing.

#### Scenario: No CUDA
- **WHEN** the text job runs without CUDA
- **THEN** it fails with `unavailable` and no rows exist
