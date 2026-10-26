"""Compatibility alias for sidetrack.external.musicbrainz."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.external.musicbrainz")
