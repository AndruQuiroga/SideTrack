"""Compatibility alias for sidetrack.analysis.taste."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.analysis.taste")
