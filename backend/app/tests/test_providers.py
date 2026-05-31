from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from backend.app.providers.base import (
    Capability,
    ConnectorError,
    FetchResult,
    HealthStatus,
    Provider,
)
from backend.app.providers.registry import ConnectorNotFound, build, list_connectors, register


class DummyProvider(Provider):
    id = "dummy"
    capabilities = Capability.PATIENT | Capability.MEDICATIONS

    def __init__(self, raise_on_health: bool = False) -> None:
        self._raise_on_health = raise_on_health

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        return FetchResult(
            bundle={"resourceType": "Bundle", "entry": [{"id": patient_id}]},
            source=self.id,
            fetched_at=datetime.now(UTC),
        )

    async def health_check(self) -> HealthStatus:
        try:
            if self._raise_on_health:
                raise RuntimeError("simulated failure")
            return HealthStatus(ok=True, latency_ms=1.0)
        except Exception as exc:
            return HealthStatus(ok=False, latency_ms=0.0, detail=str(exc))


class PartialDummyProvider(Provider):
    id = "partial_dummy"
    capabilities = Capability.PATIENT | Capability.CONDITIONS

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        return FetchResult(
            bundle={"resourceType": "Bundle", "entry": [{"id": patient_id}]},
            source=self.id,
            fetched_at=datetime.now(UTC),
            partial=True,
            warnings=["conditions not available for this patient"],
            coverage={
                "patient": {"requested": True, "returned": True},
                "conditions": {"requested": True, "returned": False},
            },
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True, latency_ms=2.0)


@pytest.fixture(autouse=True)
def clear_registry():
    import backend.app.providers.registry as _reg

    _reg._REGISTRY.clear()
    yield
    _reg._REGISTRY.clear()


def test_register_and_build_returns_correct_type():
    register("dummy", DummyProvider)
    provider = build("dummy")
    assert isinstance(provider, DummyProvider)


def test_list_connectors_reflects_registered_names():
    register("dummy", DummyProvider)
    register("partial_dummy", PartialDummyProvider)
    names = list_connectors()
    assert "dummy" in names
    assert "partial_dummy" in names


def test_build_unknown_name_raises_connector_not_found():
    with pytest.raises(ConnectorNotFound):
        build("nonexistent_connector")


def test_connector_not_found_is_connector_error():
    with pytest.raises(ConnectorError):
        build("also_nonexistent")


def test_partial_fetch_returns_non_empty_bundle_with_warnings():
    register("partial_dummy", PartialDummyProvider)
    provider = build("partial_dummy")
    result = asyncio.run(provider.fetch_patient("patient-42"))

    assert result.partial is True
    assert result.bundle is not None
    bundle = result.bundle
    assert isinstance(bundle, dict)
    assert bundle.get("entry"), "bundle must have at least one entry"
    assert len(result.warnings) >= 1


def test_coverage_shows_requested_but_not_returned_field():
    register("partial_dummy", PartialDummyProvider)
    provider = build("partial_dummy")
    result = asyncio.run(provider.fetch_patient("patient-99"))

    assert result.coverage, "coverage dict must not be empty"
    partial_fields = [
        field_name
        for field_name, flags in result.coverage.items()
        if flags.get("requested") is True and flags.get("returned") is False
    ]
    assert partial_fields, "at least one coverage field must have requested=True and returned=False"


def test_health_check_never_throws_on_failing_connector():
    failing_provider = DummyProvider(raise_on_health=True)
    status = asyncio.run(failing_provider.health_check())

    assert isinstance(status, HealthStatus)
    assert status.ok is False
    assert status.detail is not None


def test_healthy_connector_returns_ok_status():
    register("dummy", DummyProvider)
    provider = build("dummy")
    status = asyncio.run(provider.health_check())

    assert isinstance(status, HealthStatus)
    assert status.ok is True
    assert status.latency_ms >= 0.0


def test_build_passes_kwargs_to_factory():
    def factory(**kw):
        return DummyProvider(raise_on_health=kw.get("raise_on_health", False))

    register("configurable", factory)
    provider = build("configurable", raise_on_health=False)
    assert isinstance(provider, DummyProvider)


def test_supports_returns_true_for_declared_capability():
    register("dummy", DummyProvider)
    provider = build("dummy")
    assert provider.supports(Capability.PATIENT)
    assert provider.supports(Capability.MEDICATIONS)


def test_supports_returns_false_for_undeclared_capability():
    register("dummy", DummyProvider)
    provider = build("dummy")
    assert not provider.supports(Capability.OBSERVATIONS)
