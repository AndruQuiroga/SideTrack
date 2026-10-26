"""Compatibility alias for sidetrack.identity.routes.users."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.identity.routes.users")
