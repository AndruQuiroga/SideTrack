"""Compatibility alias for sidetrack.api.routes.jobs."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.api.routes.jobs")
