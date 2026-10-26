"""Compatibility alias for sidetrack.catalog.metadata."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.catalog.metadata")
