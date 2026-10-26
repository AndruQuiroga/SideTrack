"""Compatibility alias for sidetrack.external.spotify."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.external.spotify")
