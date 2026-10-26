"""Compatibility alias for sidetrack.analysis.routes.recommendations."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.analysis.routes.recommendations")
