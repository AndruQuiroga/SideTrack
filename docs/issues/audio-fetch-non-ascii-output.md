# `sidetrack.audio fetch` crashes on non-ASCII titles when output is redirected on Windows

Found during the `add-audio-benchmark-v2` owner run (2026-10-27). Violates
`openspec/specs/analysis/audio-assets`, which requires that one seed's failure never
ends a fetch run.

Running `python -m sidetrack.audio fetch --seeds …` on Windows with stdout redirected
to a file uses the console code page (cp1252). The first progress line whose artist or
title contains a character outside it raises `UnicodeEncodeError` from `print(…, file=out)`
in `sidetrack/audio.py`. The whole run ends, and later seeds are never fetched. Observed:
`≡` (U+2261) after seed 44 of 250, and `ć` (U+0107) after seed 118 of 150. Assets already
stored are kept.

Reproduce: on Windows, run fetch with a seed titled "Ćao" and redirect stdout to a file.
Expected: the progress line is written, or a replacement character is used, and the run
continues. Actual: a traceback and exit code 1.

Workaround: set `PYTHONIOENCODING=utf-8` (or `PYTHONUTF8=1`) for the run.

Fix in its own change: reconfigure the CLI's output stream to UTF-8 with
`errors="replace"` at start-up, and add a CLI test that prints a non-ASCII seed through
a cp1252 stream.
