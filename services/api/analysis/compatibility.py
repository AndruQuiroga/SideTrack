"""Compatibility alias for sidetrack.analysis.compatibility."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.analysis.compatibility")
