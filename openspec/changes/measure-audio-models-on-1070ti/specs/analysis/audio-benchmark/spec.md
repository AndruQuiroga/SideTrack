# Spec Delta

## ADDED Requirements

### Requirement: GPU compatibility is checked before a model loads
Before loading a model on a CUDA device, `audio-lab embed` SHALL check that the installed torch build has kernels for the device's compute capability. If it doesn't, or a CUDA error occurs while loading or probing the model, that model SHALL be reported unavailable with the reason, and the run SHALL continue with the next model.

#### Scenario: Torch build without the GPU's architecture
- **WHEN** `audio-lab embed` runs on a GPU of compute capability 6.1 with a torch build whose architecture list lacks `sm_61`
- **THEN** each requested model is reported unavailable with a reason naming `sm_61` and the build's architecture list, no embedding rows are written, and `run.json` is still written

#### Scenario: CUDA error during the load probe
- **WHEN** a model's probe embedding raises a CUDA error
- **THEN** that model is reported unavailable with the error message, and the run continues with the next model

### Requirement: Runs record GPU compatibility
`run.json` SHALL record, alongside the GPU name and driver, the GPU's compute capability and the torch build's CUDA architecture list.

#### Scenario: Run on a GPU
- **WHEN** a run completes on a CUDA device
- **THEN** `run.json`'s environment contains the compute capability (for example `6.1`) and the architecture list reported by torch

### Requirement: Runs can be compared for parity across hardware
`audio-lab parity RUN_A RUN_B --model M` SHALL compare M's vectors in the two runs by asset SHA-256 with cosine similarity, and report the number of shared assets, the minimum, 1st-percentile and median similarity, and the assets below a threshold (default 0.999). It MUST refuse when the runs used different checkpoint revisions or window settings for M.

#### Scenario: Same model on two GPUs
- **WHEN** parity is run for `muq-mulan` between two runs of the same manifest, revision and window settings
- **THEN** it prints the shared asset count and the minimum, 1st-percentile and median cosine, and lists every asset below 0.999 by SHA-256

#### Scenario: Different revisions
- **WHEN** the two runs recorded different checkpoint revisions for the model
- **THEN** the command exits non-zero naming both revisions and compares nothing

#### Scenario: Model missing from a run
- **WHEN** one of the runs has no rows for the requested model
- **THEN** the command exits non-zero saying which run lacks it

## MODIFIED Requirements

### Requirement: Runs record performance
For each model, a run SHALL record:
- total audio seconds processed
- wall-clock seconds
- throughput in audio seconds per second
- peak GPU memory in MiB
- the number of failed assets
- model load seconds, measured separately from wall-clock embedding time

These are measured on the hardware that ran it.

#### Scenario: Performance recorded
- **WHEN** a run completes on a GPU
- **THEN** `run.json` contains those six figures for each model, the peak GPU memory is greater than zero, and the load seconds are greater than zero and not included in the wall-clock seconds
