"""Compatibility alias for sidetrack.api.routes.search."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.api.routes.search")
