"""Compatibility alias for sidetrack.schemas.core."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.schemas.core")
