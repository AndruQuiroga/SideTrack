"""Compatibility alias for sidetrack.listening.ingest."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.listening.ingest")
