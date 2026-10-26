"""Compatibility alias for sidetrack.rq_worker."""

import importlib
import sys

_module = importlib.import_module("sidetrack.rq_worker")
if __name__ == "__main__":
    _module.main()
else:
    sys.modules[__name__] = _module
