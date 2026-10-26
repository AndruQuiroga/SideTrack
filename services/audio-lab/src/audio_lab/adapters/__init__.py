"""Model adapters, by name. Never compare vectors from different adapters (ADR 0004)."""

from .base import Adapter, AdapterInfo, ModelUnavailable, pool
from .models import CLAPAdapter, MERTAdapter, MuQAdapter, MuQMuLanAdapter

ADAPTERS: dict[str, type[Adapter]] = {
    cls.name: cls for cls in (MuQAdapter, MuQMuLanAdapter, MERTAdapter, CLAPAdapter)
}


def get_adapter(name: str) -> Adapter:
    try:
        return ADAPTERS[name]()
    except KeyError:
        raise KeyError(f"unknown model {name!r}; choose from {', '.join(ADAPTERS)}") from None


__all__ = ["ADAPTERS", "Adapter", "AdapterInfo", "ModelUnavailable", "get_adapter", "pool"]
