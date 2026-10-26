"""Compatibility alias for sidetrack.analysis.routes.compatibility."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.analysis.routes.compatibility")
