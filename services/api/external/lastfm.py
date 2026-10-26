"""Compatibility alias for sidetrack.external.lastfm."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.external.lastfm")
