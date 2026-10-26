"""Compatibility alias for sidetrack.listening.routes.listen_events."""

import importlib
import sys

sys.modules[__name__] = importlib.import_module("sidetrack.listening.routes.listen_events")
