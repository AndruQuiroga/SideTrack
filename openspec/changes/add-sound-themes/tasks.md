# Tasks

## 1. Text vectors

- [ ] 1.1 Add vocabulary v1 and the `analysis.embed_text` GPU job; verify `tests/test_text_embeddings.py` incl. the unavailable scenario

## 2. Themes

- [ ] 2.1 Implement clustering, naming, tags and rename; verify `tests/test_sound_themes.py` covers stable rebuild, small library, naming and rename
- [ ] 2.2 Run on production, record theme count and coverage in docs/AUDIO.md, update docs/status.yaml and regenerate STATUS; verify `make lint` and `make test.unit`

## Workflow follow-up

- Archive the change once every scenario has a passing test.
