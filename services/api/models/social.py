"""Compatibility alias for sidetrack.models."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.models")
