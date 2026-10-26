"""Compatibility alias for sidetrack.club.routes.votes."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.club.routes.votes")
