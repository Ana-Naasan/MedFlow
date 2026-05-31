"""Contract and audit tests for POST /intake."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.cache.models import AuditEvent
from backend.app.main import app


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


_HEADERS = {"Authorization": "Bearer PLACEHOLDER"}


def test_post_intake_returns_201_and_patient_id():
    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={"connector": "mock-fhir", "source_patient_id": "DEMO-001"},
            headers=_HEADERS,
        )
    assert resp.status_code == 201
    body = resp.json()
    assert "patient_id" in body
    assert body["status"] == "registered"
    assert body["resource_count"] > 0
    assert isinstance(body["hypothesis_ids"], list)
    assert len(body["hypothesis_ids"]) > 0


def test_post_intake_patient_appears_in_get_patients():
    with TestClient(app) as client:
        intake_resp = client.post(
            "/intake",
            json={"connector": "mock-fhir", "source_patient_id": "DEMO-001"},
            headers=_HEADERS,
        )
        assert intake_resp.status_code == 201
        new_patient_id = intake_resp.json()["patient_id"]

        patients_resp = client.get("/patients", headers=_HEADERS)
    assert patients_resp.status_code == 200
    patient_ids = [p["id"] for p in patients_resp.json()]
    assert new_patient_id in patient_ids


def test_post_intake_with_explicit_patient_id():
    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={
                "connector": "mock-fhir",
                "source_patient_id": "DEMO-001",
                "patient_id": "explicit-patient-xyz",
            },
            headers=_HEADERS,
        )
    assert resp.status_code == 201
    assert resp.json()["patient_id"] == "explicit-patient-xyz"


def test_post_intake_unknown_connector_returns_404():
    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={"connector": "does-not-exist", "source_patient_id": "DEMO-001"},
            headers=_HEADERS,
        )
    assert resp.status_code == 404


def test_post_intake_writes_audit_event():
    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={"connector": "mock-fhir", "source_patient_id": "DEMO-001"},
            headers=_HEADERS,
        )
        assert resp.status_code == 201
        patient_id = resp.json()["patient_id"]

        # Query the DB using the app's own session_factory (same engine as the request).
        factory = app.state.session_factory

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(AuditEvent).where(
                        AuditEvent.event_type == "intake_registered",
                        AuditEvent.patient_id == patient_id,
                    )
                )
                return result.scalars().all()

        events = asyncio.run(_check())
    assert len(events) == 1
    assert events[0].event_type == "intake_registered"
