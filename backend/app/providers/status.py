"""Live connector inventory with real health probing (API-05).

Replaces the static ``cache.store.STATIC_CONNECTORS`` list behind ``GET /connectors``.
Iterates the live provider registry so every registered connector self-advertises
(mock-fhir, pdf, hl7v2, institution-a, institution-b) and runs each provider's
``health_check()`` concurrently — bounded by a timeout so an unreachable source can
never hang the endpoint. The reported health is real, not hardcoded.

The served shape is deliberately slim — ``{id, name, capabilities, health, latency_ms}`` —
and never echoes ``HealthStatus.detail``, which can carry raw infrastructure errors
(e.g. a DSN host/port); that stays internal, matching the project's SEC-02 discipline.
``id`` is the registry connector name (not ``provider.id``, which is ``"postgres"`` for
both institution connectors and would collide).
"""

from __future__ import annotations

import asyncio

from backend.app.providers.base import Capability, Provider
from backend.app.providers.registry import build, list_connectors

# Upper bound on a single connector's health probe. asyncpg/httpx can stall on an
# unreachable host; without this the status endpoint would inherit that stall.
_HEALTH_TIMEOUT_S = 5.0


def _capability_names(provider: Provider) -> list[str]:
    """Supported capability names in Capability declaration order."""
    return [cap.name for cap in Capability if provider.supports(cap)]


async def _probe(name: str) -> dict[str, object]:
    """Build one registered connector and probe its health, never raising."""
    try:
        provider = build(name)
    except Exception:
        # A registration/build failure still surfaces the connector — as down,
        # with no capabilities — rather than vanishing from the inventory.
        return {
            "id": name,
            "name": name,
            "capabilities": [],
            "health": "down",
            "latency_ms": 0.0,
        }

    try:
        try:
            result = await asyncio.wait_for(provider.health_check(), timeout=_HEALTH_TIMEOUT_S)
            ok, latency_ms = result.ok, result.latency_ms
        except TimeoutError:
            ok, latency_ms = False, _HEALTH_TIMEOUT_S * 1000
        except Exception:
            ok, latency_ms = False, 0.0

        return {
            "id": name,
            "name": type(provider).__name__,
            "capabilities": _capability_names(provider),
            "health": "ok" if ok else "down",
            "latency_ms": round(latency_ms, 2),
        }
    finally:
        # The prober owns this throwaway instance — release anything its health
        # check opened (e.g. a Postgres pool) so /connectors can't leak connections.
        await provider.aclose()


async def list_connector_status() -> list[dict[str, object]]:
    """Every registered connector with a real health probe, in registry order."""
    names = list_connectors()
    return list(await asyncio.gather(*(_probe(name) for name in names)))
