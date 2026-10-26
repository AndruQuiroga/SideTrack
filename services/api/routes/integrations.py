"""Compatibility alias for sidetrack.identity.routes.integrations."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.identity.routes.integrations")
