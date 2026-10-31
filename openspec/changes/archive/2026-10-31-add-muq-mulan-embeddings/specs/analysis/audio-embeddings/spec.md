# Spec Delta

## Purpose

Defines how Sidetrack turns acquired audio assets into audio embeddings on the GPU queue,
stores them in Postgres with their provenance, reports models it can't run, and ranks
similar audio within one model.

## ADDED Requirements

### Requirement: Embeddings are stored per asset and model with provenance
Each stored embedding SHALL belong to one audio asset and one model, and record the model's checkpoint revision, the preprocessing pipeline version, the vector's dimension, the job that produced it and when. An asset SHALL have at most one embedding per model. The vector's length MUST equal its recorded dimension.

#### Scenario: Embedding an asset
- **WHEN** the GPU worker embeds an asset with MuQ-MuLan
- **THEN** one embedding row exists for that asset and model, with a 512-dimension unit-length vector, the pinned checkpoint revision, the pipeline version, the job ID and a timestamp

#### Scenario: Wrong dimension rejected
- **WHEN** a row whose vector length differs from its recorded dimension is written
- **THEN** the database rejects it and no row is stored

### Requirement: Only enabled models are embedded
The system SHALL embed only models on its enabled list, which in this capability is MuQ-MuLan alone. Asking to embed any other model MUST fail before any job is queued, naming the enabled models.

#### Scenario: Asking for a model that isn't enabled
- **WHEN** the operator runs the embed command with model `muq`
- **THEN** the command exits non-zero naming `muq-mulan` as the enabled model, and no job is queued

### Requirement: Embedding runs only on the GPU queue
Embedding jobs SHALL be queued on the `gpu` queue and run only by a worker started for that queue alone. A CPU worker MUST leave them unclaimed.

#### Scenario: CPU worker running
- **WHEN** an embedding job is queued and only a CPU worker (default and musicbrainz queues) is running
- **THEN** the job stays queued, and no embedding row is written

### Requirement: Unavailable models are reported, never faked
When the model's libraries, weights or GPU can't be loaded, the embedding job SHALL fail with the safe error `unavailable` and store no embedding for any asset in it. No code path MAY store constant, random or placeholder vectors.

#### Scenario: GPU worker without CUDA
- **WHEN** an embedding job runs on a GPU worker where CUDA is not available
- **THEN** the job's status is failed with error `unavailable`, it is not retried, and no embedding rows exist for its assets

#### Scenario: Model libraries missing
- **WHEN** an embedding job runs in an environment without the model libraries installed
- **THEN** the job fails with error `unavailable` and no embedding rows are written

### Requirement: One bad asset doesn't fail a batch
An asset whose file is missing, pruned or undecodable SHALL be skipped with a reason code (`missing_file`, `file_deleted` or `decode_failed`) in the job result. The other assets in the batch SHALL still be embedded, and the job SHALL finish.

#### Scenario: Batch with a pruned file
- **WHEN** a job embeds 3 assets and one of them has had its file pruned
- **THEN** the job finishes, 2 embedding rows are written, and the job result lists the third asset with reason `file_deleted`

### Requirement: Embedding is idempotent and revision-aware
An asset whose embedding for a model already has the current checkpoint revision and pipeline version SHALL be skipped. An embedding made with an older revision or pipeline SHALL be replaced when that asset is embedded again.

#### Scenario: Job runs twice
- **WHEN** the same embedding job's assets are embedded a second time with no change to the model
- **THEN** the embedding rows are unchanged, and the second result reports those assets as already current

#### Scenario: Revision changed
- **WHEN** an asset's stored embedding has an older checkpoint revision than the enabled model's
- **THEN** the embed command counts it as missing, and embedding it replaces the row with one carrying the current revision

### Requirement: Backfill is started explicitly by the operator
Embedding jobs SHALL be queued only by the operator's embed command, for assets that have a file on disk and no current embedding, split into batches. No schedule, API route or bot command SHALL queue embedding.

#### Scenario: Backfilling
- **WHEN** 5 assets have files, 2 of them already have current embeddings, and the operator runs the embed command
- **THEN** jobs covering exactly the 3 other assets are queued on the `gpu` queue, and the command prints the job IDs and the asset count

#### Scenario: Nothing schedules embedding
- **WHEN** the worker's registered tasks and persisted schedules are listed
- **THEN** no schedule queues an embedding job

### Requirement: Production vectors match the benchmark pipeline
For the same audio file and checkpoint revision, the production embedding SHALL use the benchmark's decoding, 10-second windows, 180-second cap, fp32 inference, mean pooling and L2 normalisation, so that its vector agrees with the benchmark run's vector for that file.

#### Scenario: Parity with run c7c3698
- **WHEN** assets embedded in benchmark run `20261027-031711-c7c3698` are embedded by the GPU worker
- **THEN** each production vector has cosine similarity of at least 0.999 with that run's MuQ-MuLan vector for the same SHA-256

### Requirement: Neighbours are ranked within one model and revision
The similar-audio operation SHALL rank other assets by cosine similarity among embeddings of the same model, revision and pipeline only, highest first, and return at most the requested number. It SHALL exclude assets of the query asset's own track, or of its seed artist and title when it has no track.

#### Scenario: Own preview excluded
- **WHEN** neighbours are requested for a full track whose preview is also embedded
- **THEN** the preview does not appear in the result, and every result has a similarity no higher than the one before it

#### Scenario: Other models ignored
- **WHEN** neighbours are requested with model `muq-mulan` and the table also holds rows for another model or an older revision
- **THEN** only rows with MuQ-MuLan's current revision and pipeline are ranked

#### Scenario: Asset not embedded
- **WHEN** neighbours are requested for an asset with no current embedding for the model
- **THEN** the operation reports that the asset is not embedded and returns no neighbours

### Requirement: Embeddings follow their asset's lifetime
An embedding SHALL remain when its asset's file is pruned, because the asset row remains. Deleting an asset row SHALL delete its embeddings.

#### Scenario: File pruned
- **WHEN** prune deletes the file of an embedded asset
- **THEN** its embedding row remains and the asset still appears in neighbour results

#### Scenario: Asset deleted
- **WHEN** an embedded asset's row is deleted
- **THEN** none of its embedding rows remain
