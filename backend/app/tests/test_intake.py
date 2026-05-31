"""Contract tests for POST /intake."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.cache.models import AuditEvent
from backend.app.providers import registry
from backend.app.providers.base import Capability, FetchResult, HealthStatus, Provider


class _StubProvider(Provider):
    id = "stub"
    capabilities = Capability.PATIENT | Capability.MEDICATIONS

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        return FetchResult(
            bundle={
                "resourceType": "Bundle",
                "type": "searchset",
                "entry": [
                    {"resource": {"resourceType": "Patient", "id": patient_id}},
                    {
                        "resource": {
                            "resourceType": "MedicationStatement",
                            "id": "med-stub-1",
                            "status": "active",
                            "subject": {"reference": f"Patient/{patient_id}"},
                        }
                    },
                ],
            },
            source=self.id,
            fetched_at=datetime.now(UTC),
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True, latency_ms=0.0)


@pytest.fixture(autouse=True)
def _set_dev_token(monkeypatch):
    monkeypatch.setenv("DEV_TOKEN", "test-token")
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "fake")
    monkeypatch.setenv("OPENFDA_API_KEY", "fake")


@pytest.fixture
def stub_connector():
    registry.register("stub-fhir", _StubProvider)
    yield "stub-fhir"
    registry._REGISTRY.pop("stub-fhir", None)


def test_post_intake_returns_201_and_patient_id(stub_connector):
    from backend.app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={"connector": stub_connector, "source_patient_id": "SRC-001"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "registered"
    assert "patient_id" in body
    assert body["resource_count"] >= 1
    assert isinstance(body["hypothesis_ids"], list)


def test_post_intake_patient_appears_in_get_patients(stub_connector):
    from backend.app.main import app

    with TestClient(app) as client:
        intake_resp = client.post(
            "/intake",
            json={"connector": stub_connector, "source_patient_id": "SRC-002"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert intake_resp.status_code == 201
        new_patient_id = intake_resp.json()["patient_id"]

        patients_resp = client.get(
            "/patients",
            headers={"Authorization": "Bearer test-token"},
        )

    assert patients_resp.status_code == 200
    patient_ids = [p["id"] for p in patients_resp.json()]
    assert new_patient_id in patient_ids


def test_post_intake_with_explicit_patient_id(stub_connector):
    from backend.app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={
                "connector": stub_connector,
                "source_patient_id": "SRC-003",
                "patient_id": "our-pat-custom",
            },
            headers={"Authorization": "Bearer test-token"},
        )

    assert resp.status_code == 201
    assert resp.json()["patient_id"] == "our-pat-custom"


def test_post_intake_unknown_connector_returns_404():
    from backend.app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={"connector": "no-such-connector", "source_patient_id": "x"},
            headers={"Authorization": "Bearer test-token"},
        )

    assert resp.status_code == 404


def test_post_intake_writes_audit_event(stub_connector):
    """Intake writes an intake_registered audit event."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from backend.app.cache.models import Base

    async def _run():
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        from backend.app.main import create_app

        app = create_app()

        with TestClient(app) as client:
            # Override the factory AFTER lifespan startup so requests use our DB.
            app.state.session_factory = factory
            resp = client.post(
                "/intake",
                json={"connector": stub_connector, "source_patient_id": "SRC-AUDIT"},
                headers={"Authorization": "Bearer test-token"},
            )
        assert resp.status_code == 201

        async with factory() as sess:
            count = (
                await sess.execute(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.event_type == "intake_registered")
                )
            ).scalar_one()
            assert count == 1

        await engine.dispose()

    asyncio.run(_run())
