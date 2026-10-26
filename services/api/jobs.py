"""Compatibility alias for sidetrack.jobs."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.jobs")
