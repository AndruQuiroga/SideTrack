"""Compatibility alias for sidetrack.identity.link_state."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.identity.link_state")
