"""Registry and helpers for ingestion providers."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any, Type

# Discover provider classes under the ``providers`` subpackage.  Providers
# should expose classes with names ending in ``Ingester``.  The provider name is
# derived from the class name (``SpotifyIngester`` -> ``spotify``) unless the
# class defines a ``provider`` attribute.


def _discover() -> dict[str, Type[Any]]:
    providers: dict[str, Type[Any]] = {}
    pkg = importlib.import_module("sidetrack.services.providers")
    for modinfo in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        module = importlib.import_module(modinfo.name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.endswith("Ingester"):
                provider_name = getattr(obj, "provider", name[:-8]).lower()
                providers[provider_name] = obj
    return providers


PROVIDERS = _discover()


def get_ingester(name: str, /, **kwargs: Any) -> Any:
    """Instantiate an ingester by name.

    Parameters
    ----------
    name:
        Identifier for the desired provider (e.g. ``"spotify"``).
    **kwargs:
        Optional keyword arguments passed to the provider class constructor.
    """
    cls = PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown ingester '{name}'")
    return cls(**kwargs)


__all__ = ["get_ingester", "PROVIDERS"]
