"""Compatibility alias for sidetrack.config."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.config")
