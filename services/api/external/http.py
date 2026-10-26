"""Compatibility alias for sidetrack.external.http."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.external.http")
