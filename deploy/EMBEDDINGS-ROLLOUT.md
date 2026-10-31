# Embeddings rollout, 2026-10-31

## Audio and import

- 883 local files matched the manifest exactly. The 21 AcoustID mismatches stayed off the rack.
- 862 files were copied to docker-0 and moved to the audio HDD. Every SHA-256 was checked on
  arrival and again on the HDD.
- `import-manifest` check: 862 new, 0 existing, 0 rejected, 0 conflicting.
- Apply imported 862 assets. The retry reported 0 new and 862 existing.
- Weeks, users, albums, linked accounts and ratings had the same row counts before and after.

## GPU worker

Only the `gpu-worker` image changed, to release e9f03e0 pinned by digest, through Portainer. All
ten stack environment entries were preserved, and the stack's other images are unchanged.

## Embedding

- The first job downloaded the weights and stored a 512-dimension unit vector at the pinned
  revision, about 4 minutes after the worker started.
- The backfill of the other 861 assets took 21 minutes in 7 jobs on the GTX 1070.
- All 8 jobs finished on their first attempt. 862 of 862 assets have an embedding, with no
  failures, one model revision, and every vector at unit length.
- Spot checks on three tracks from different genres returned neighbours in the same genre. One
  track's nearest results included its own preview.
- The model loads with Hugging Face access disabled, so offline mode is safe to set.

## Offline mode

`SIDETRACK_HF_OFFLINE=1` was set through Portainer after the model loaded with Hugging Face
access disabled. The other nine environment entries are unchanged, and all six services are 1/1.
