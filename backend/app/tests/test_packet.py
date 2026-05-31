from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


def _client() -> TestClient:
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer PLACEHOLDER"}


def test_packet_endpoint_returns_cited_suggestions_and_cache_header() -> None:
    response = _client().get("/patients/pat-001/packet", headers=_auth_headers())

    assert response.status_code == 200
    assert response.headers["x-cache"] == "HIT"
    payload = response.json()
    assert payload["patient_id"] == "pat-001"
    assert payload["hypotheses"]
    assert payload["hypotheses"][0]["citations"]


def test_patient_and_evidence_citations_resolve() -> None:
    client = _client()

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


def test_list_patients_connectors_and_refresh() -> None:
    client = _client()
    patients = client.get("/patients", headers=_auth_headers())
    connectors = client.get("/connectors", headers=_auth_headers())
    refresh = client.post("/patients/pat-001/refresh", headers=_auth_headers())

    assert patients.status_code == 200
    assert connectors.status_code == 200
    assert refresh.status_code == 200
    assert refresh.headers["x-cache"] == "REFRESH"
