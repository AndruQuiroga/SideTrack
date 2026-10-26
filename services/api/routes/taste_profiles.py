"""Compatibility alias for sidetrack.analysis.routes.taste_profiles."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.analysis.routes.taste_profiles")
