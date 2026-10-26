"""Compatibility alias for sidetrack.api.routes.feed."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.api.routes.feed")
