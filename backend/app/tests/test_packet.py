from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


@pytest.fixture(autouse=True)
def abstain_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the reasoning pipeline to abstain so /packet serves the static
    scaffold here — keeps these tests deterministic and offline (no Gemini call).
    The live reasoned path is covered by test_packet_reasoning.py."""

    async def _no_hypotheses(*args: object, **kwargs: object) -> list:
        return []

    monkeypatch.setattr("backend.app.reasoning.pipeline.run_reasoning", _no_hypotheses)


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


def test_packet_for_unknown_patient_serves_no_unresolvable_citation() -> None:
    # A non-static patient's default scaffold hardcodes a Patient/pat-001 citation
    # that does NOT resolve for them. The fallback must run it through the
    # cache-authoritative gate and abstain — never serve an unresolvable citation.
    with TestClient(app) as client:
        resp = client.get("/patients/ghost-patient/packet", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        for hyp in body["hypotheses"]:
            for citation in hyp["citations"]:
                if citation["kind"] == "resource":
                    rtype, _, rid = citation["ref"].partition("/")
                    res = client.get(
                        f"/patients/ghost-patient/resource/{rtype}/{rid}",
                        headers=_auth_headers(),
                    )
                    assert res.status_code == 200, f"unresolvable citation {citation['ref']}"
    # The scaffold's only hypothesis cites Patient/pat-001 → dropped → abstains.
    assert body["hypotheses"] == []


def test_list_patients_connectors_and_refresh() -> None:
    with TestClient(app) as client:
        patients = client.get("/patients", headers=_auth_headers())
        connectors = client.get("/connectors", headers=_auth_headers())
        refresh = client.post("/patients/pat-001/refresh", headers=_auth_headers())

    assert patients.status_code == 200
    assert connectors.status_code == 200
    assert refresh.status_code == 200
    assert refresh.headers["x-cache"] == "REFRESH"


def test_audit_endpoint_returns_logged_events() -> None:
    with TestClient(app) as client:
        # A packet fetch writes a "resource_read" audit row for the DecisionPacket.
        packet = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert packet.status_code == 200

        audit = client.get("/audit", headers=_auth_headers())

    assert audit.status_code == 200
    events = audit.json()
    assert isinstance(events, list)
    assert len(events) >= 1
    first = events[0]
    assert set(first) == {
        "id",
        "event_type",
        "patient_id",
        "resource_ref",
        "actor",
        "occurred_at",
    }
    refs = {e["resource_ref"] for e in events}
    assert "DecisionPacket/pat-001" in refs


def test_audit_endpoint_requires_auth() -> None:
    with TestClient(app) as client:
        resp = client.get("/audit")
    assert resp.status_code == 401


def test_audit_endpoint_accepts_valid_limit() -> None:
    with TestClient(app) as client:
        packet = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert packet.status_code == 200

        audit = client.get("/audit?limit=10", headers=_auth_headers())

    assert audit.status_code == 200
    events = audit.json()
    assert isinstance(events, list)
    assert len(events) <= 10


@pytest.mark.parametrize("limit", [-1, 0, 99999])
def test_audit_endpoint_rejects_out_of_range_limit(limit: int) -> None:
    # Query(ge=1, le=200) rejects out-of-range values at the boundary (422)
    # before they reach SQL — a negative SQLite LIMIT means UNLIMITED, and a
    # huge limit causes an unbounded fetch; both must be blocked.
    with TestClient(app) as client:
        resp = client.get(f"/audit?limit={limit}", headers=_auth_headers())
    assert resp.status_code == 422
