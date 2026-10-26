"""Compatibility alias for sidetrack.db."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.db")
