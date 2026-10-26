"""Compatibility alias for sidetrack.catalog.routes.albums."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.catalog.routes.albums")
