from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer PLACEHOLDER"}


def test_packet_endpoint_hit_refresh_lifecycle() -> None:
    # Use a persistent client so the lifespan (and in-memory DB) is shared.
    with TestClient(app) as client:
        # Empty DB → first call fetches from source → REFRESH.
        first = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert first.status_code == 200
        assert first.headers["x-cache"] == "REFRESH"
        payload = first.json()
        assert payload["patient_id"] == "pat-001"
        assert payload["cache_status"] == "REFRESH"
        assert payload["hypotheses"]
        assert payload["hypotheses"][0]["citations"]

        # Cache is now warm → second call serves from DB → HIT.
        second = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert second.status_code == 200
        assert second.headers["x-cache"] == "HIT"
        assert second.json()["cache_status"] == "HIT"


def test_patient_and_evidence_citations_resolve() -> None:
    with TestClient(app) as client:
        patient_response = client.get(
            "/patients/pat-001/resource/Patient/pat-001",
            headers=_auth_headers(),
        )
        evidence_response = client.get(
            "/evidence/openfda-label-amitriptyline",
            headers=_auth_headers(),
        )

    assert patient_response.status_code == 200
    assert patient_response.json()["id"] == "pat-001"
    assert evidence_response.status_code == 200
    assert evidence_response.json()["id"] == "openfda-label-amitriptyline"


def test_pdf_sourced_resource_includes_span() -> None:
    with TestClient(app) as client:
        resp = client.get(
            "/patients/DEMO-001/resource/MedicationStatement/med-warfarin",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "span" in body
    span = body["span"]
    assert span["page"] == 2
    assert span["snippet"] == "Warfarin 5 mg oral Anticoagulant Daily"


def test_demo_001_evidence_card_resolves() -> None:
    with TestClient(app) as client:
        resp = client.get("/evidence/ddinter-warfarin-aspirin", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["id"] == "ddinter-warfarin-aspirin"


def test_packet_includes_completeness() -> None:
    with TestClient(app) as client:
        resp = client.get("/patients/pat-001/packet", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert "completeness" in body
    completeness = body["completeness"]
    assert isinstance(completeness, list)
    assert len(completeness) >= 1
    first = completeness[0]
    assert "category" in first
    assert "documented" in first


def test_list_patients_connectors_and_refresh() -> None:
    with TestClient(app) as client:
        patients = client.get("/patients", headers=_auth_headers())
        connectors = client.get("/connectors", headers=_auth_headers())
        refresh = client.post("/patients/pat-001/refresh", headers=_auth_headers())

    assert patients.status_code == 200
    assert connectors.status_code == 200
    assert refresh.status_code == 200
    assert refresh.headers["x-cache"] == "REFRESH"
