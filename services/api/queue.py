"""Compatibility alias for sidetrack.queue."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.queue")
