"""Compatibility alias for sidetrack.analysis.constants."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.analysis.constants")
