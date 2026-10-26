"""Compatibility alias for sidetrack.api.main."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.api.main")
