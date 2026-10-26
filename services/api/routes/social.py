"""Compatibility alias for sidetrack.identity.routes.social."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.identity.routes.social")
