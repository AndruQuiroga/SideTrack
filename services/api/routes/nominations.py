"""Compatibility alias for sidetrack.club.routes.nominations."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.club.routes.nominations")
