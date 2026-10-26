"""Compatibility alias for sidetrack.listening.routes.ingest."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.listening.routes.ingest")
