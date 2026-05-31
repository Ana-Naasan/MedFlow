from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.app.providers.base import ConnectorError, Provider


class ConnectorNotFound(ConnectorError):
    """Raised when no connector is registered under the requested name."""


_REGISTRY: dict[str, Callable[..., Provider]] = {}


def register(name: str, factory: Callable[..., Provider]) -> None:
    _REGISTRY[name] = factory


def build(name: str, **kwargs: Any) -> Provider:
    factory = _REGISTRY.get(name)
    if factory is None:
        raise ConnectorNotFound(f"No connector registered under {name!r}")
    return factory(**kwargs)


def list_connectors() -> list[str]:
    return list(_REGISTRY)
