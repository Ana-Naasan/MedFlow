from __future__ import annotations

import asyncio

from backend.app.providers import status
from backend.app.providers.base import Capability, HealthStatus, Provider
from backend.app.providers.mock_fhir import MockFHIRProvider
from backend.app.providers.postgres import PostgresProvider
from backend.app.providers.registry import ConnectorNotFound


class _FakeProvider(Provider):
    """A stand-in provider whose health_check is fully controllable.

    Lives in the test module (not measured by the coverage gate), so it can model
    the ok / unhealthy / raising / hanging cases _probe must handle.
    """

    id = "fake"
    capabilities = Capability.PATIENT | Capability.CONDITIONS

    def __init__(self, *, result=None, exc=None, sleep=0.0):
        self._result = result
        self._exc = exc
        self._sleep = sleep

    async def fetch_patient(self, patient_id):
        raise NotImplementedError

    async def health_check(self):
        if self._sleep:
            await asyncio.sleep(self._sleep)
        if self._exc is not None:
            raise self._exc
        return self._result


class _SpyProvider(_FakeProvider):
    """A fake that records how many times the prober closed it."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.closed = 0

    async def aclose(self):
        self.closed += 1


class _FakePool:
    """Minimal stand-in for an asyncpg pool — records terminate()."""

    def __init__(self):
        self.terminated = False

    def terminate(self):
        self.terminated = True


def test_capability_names_lists_supported_caps_in_declaration_order():
    provider = _FakeProvider(result=HealthStatus(ok=True, latency_ms=1.0))
    # capabilities = PATIENT | CONDITIONS — PATIENT is declared before CONDITIONS,
    # and MEDICATIONS (between them) must be skipped because it isn't supported.
    assert status._capability_names(provider) == ["PATIENT", "CONDITIONS"]


def test_probe_reports_ok_with_slim_shape(monkeypatch):
    provider = _FakeProvider(result=HealthStatus(ok=True, latency_ms=2.5, detail="secret-dsn-host"))
    monkeypatch.setattr(status, "build", lambda name: provider)

    result = asyncio.run(status._probe("mock-fhir"))

    # Slim contract: no raw `detail` echoed (SEC-02 — it may carry infra errors).
    assert result == {
        "id": "mock-fhir",
        "name": "_FakeProvider",
        "capabilities": ["PATIENT", "CONDITIONS"],
        "health": "ok",
        "latency_ms": 2.5,
    }


def test_probe_reports_down_when_unhealthy(monkeypatch):
    provider = _FakeProvider(result=HealthStatus(ok=False, latency_ms=0.0, detail="refused"))
    monkeypatch.setattr(status, "build", lambda name: provider)

    result = asyncio.run(status._probe("institution-a"))

    assert result["health"] == "down"
    assert "detail" not in result


def test_probe_reports_down_when_health_check_raises(monkeypatch):
    provider = _FakeProvider(exc=RuntimeError("boom"))
    monkeypatch.setattr(status, "build", lambda name: provider)

    result = asyncio.run(status._probe("mock-fhir"))

    assert result["health"] == "down"
    assert result["latency_ms"] == 0.0


def test_probe_reports_down_on_timeout(monkeypatch):
    # A health_check that never returns must not hang the endpoint.
    provider = _FakeProvider(result=HealthStatus(ok=True, latency_ms=0.0), sleep=1.0)
    monkeypatch.setattr(status, "build", lambda name: provider)
    monkeypatch.setattr(status, "_HEALTH_TIMEOUT_S", 0.01)

    result = asyncio.run(status._probe("mock-fhir"))

    assert result["health"] == "down"


def test_probe_reports_down_when_build_fails(monkeypatch):
    def _boom(name):
        raise ConnectorNotFound(f"no connector {name!r}")

    monkeypatch.setattr(status, "build", _boom)

    result = asyncio.run(status._probe("ghost"))

    assert result["id"] == "ghost"
    assert result["name"] == "ghost"
    assert result["capabilities"] == []
    assert result["health"] == "down"


def test_probe_closes_the_provider_it_built(monkeypatch):
    # The prober owns the throwaway provider it build()s, so it must release any
    # resource that provider opened (e.g. an asyncpg pool created by a DB health
    # check) — otherwise every /connectors hit leaks connections.
    provider = _SpyProvider(result=HealthStatus(ok=True, latency_ms=1.0))
    monkeypatch.setattr(status, "build", lambda name: provider)

    asyncio.run(status._probe("institution-a"))

    assert provider.closed == 1


def test_probe_closes_the_provider_even_on_timeout(monkeypatch):
    # The leak-prone path: a slow health check is cancelled by the timeout, but the
    # provider must still be closed in a finally.
    provider = _SpyProvider(result=HealthStatus(ok=True, latency_ms=0.0), sleep=1.0)
    monkeypatch.setattr(status, "build", lambda name: provider)
    monkeypatch.setattr(status, "_HEALTH_TIMEOUT_S", 0.01)

    asyncio.run(status._probe("institution-a"))

    assert provider.closed == 1


def test_postgres_aclose_terminates_a_created_pool():
    fake_pool = _FakePool()
    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=fake_pool)

    asyncio.run(provider.aclose())

    assert fake_pool.terminated is True
    assert provider._pool is None


def test_postgres_aclose_without_a_pool_is_a_safe_noop():
    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=None)

    asyncio.run(provider.aclose())  # must not raise

    assert provider._pool is None


def test_list_connector_status_preserves_registry_order(monkeypatch):
    fakes = {
        "a": _FakeProvider(result=HealthStatus(ok=True, latency_ms=1.0)),
        "b": _FakeProvider(result=HealthStatus(ok=False, latency_ms=0.0)),
    }
    monkeypatch.setattr(status, "list_connectors", lambda: ["a", "b"])
    monkeypatch.setattr(status, "build", lambda name: fakes[name])

    result = asyncio.run(status.list_connector_status())

    assert [c["id"] for c in result] == ["a", "b"]
    assert result[0]["health"] == "ok"
    assert result[1]["health"] == "down"


def test_list_connector_status_advertises_all_registered_connectors(monkeypatch):
    # Exercise the REAL registry; only neutralise the two health checks that do
    # network/DB I/O (mock-fhir → HAPI, postgres → asyncpg) so this stays offline.
    async def _ok(self):
        return HealthStatus(ok=True, latency_ms=0.1)

    monkeypatch.setattr(MockFHIRProvider, "health_check", _ok)
    monkeypatch.setattr(PostgresProvider, "health_check", _ok)

    result = asyncio.run(status.list_connector_status())

    by_id = {c["id"]: c for c in result}
    # All five live connectors self-advertise (closes the static list's gap, which
    # listed only mock-fhir + a non-existent "postgres").
    assert [c["id"] for c in result] == [
        "mock-fhir",
        "pdf",
        "hl7v2",
        "institution-a",
        "institution-b",
    ]
    # mock-fhir really supports all six categories (the old static list understated
    # it as three — part of why the static list was wrong).
    assert by_id["mock-fhir"]["capabilities"] == [
        "PATIENT",
        "MEDICATIONS",
        "CONDITIONS",
        "ALLERGIES",
        "OBSERVATIONS",
        "PROCEDURES",
    ]
    assert by_id["institution-a"]["name"] == "PostgresProvider"
    assert by_id["institution-a"]["capabilities"] == [
        "PATIENT",
        "MEDICATIONS",
        "CONDITIONS",
        "ALLERGIES",
        "OBSERVATIONS",
        "PROCEDURES",
    ]
    assert all(c["health"] == "ok" for c in result)
