"""Compatibility alias for sidetrack.club.routes.admin."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.club.routes.admin")
