"""Contract and audit tests for POST /intake."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.cache import repo
from backend.app.cache.models import AuditEvent, CachedResource, HypothesisRecord
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


def test_intake_audit_actor_is_token_subject():
    # API-07: the intake_registered audit event records the token subject, not actor="api".
    from backend.app.api.auth import dev_token_subject

    expected = dev_token_subject("PLACEHOLDER")
    with TestClient(app) as client:
        factory = app.state.session_factory
        resp = client.post(
            "/intake",
            json={"connector": "mock-fhir", "source_patient_id": "DEMO-001"},
            headers=_HEADERS,
        )
        assert resp.status_code == 201

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    select(AuditEvent).where(AuditEvent.event_type == "intake_registered")
                )
                return result.scalars().all()

        events = asyncio.run(_check())
    actors = {e.actor for e in events}
    assert actors == {expected}
    assert "api" not in actors


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


def test_reintake_same_patient_is_idempotent():
    """Re-running intake for the same patient_id yields identical hypothesis ids
    (deterministic) and creates no duplicate hypothesis rows."""
    with TestClient(app) as client:
        first = client.post(
            "/intake",
            json={
                "connector": "mock-fhir",
                "source_patient_id": "DEMO-001",
                "patient_id": "reintake-pat",
            },
            headers=_HEADERS,
        )
        second = client.post(
            "/intake",
            json={
                "connector": "mock-fhir",
                "source_patient_id": "DEMO-001",
                "patient_id": "reintake-pat",
            },
            headers=_HEADERS,
        )

        factory = app.state.session_factory

        async def _rows():
            async with factory() as session:
                result = await session.execute(
                    select(HypothesisRecord).where(HypothesisRecord.patient_id == "reintake-pat")
                )
                return result.scalars().all()

        rows = asyncio.run(_rows())

    assert first.status_code == 201
    assert second.status_code == 201
    first_ids = first.json()["hypothesis_ids"]
    second_ids = second.json()["hypothesis_ids"]
    assert first_ids and first_ids == second_ids  # deterministic, stable across re-intake
    assert len(rows) == len(first_ids)  # no duplicate hypothesis rows


def test_intake_resources_are_resolvable_as_citations():
    """End-to-end (API-02): a mock-fhir intake persists FHIR resources that are
    then resolvable via /patients/{id}/resource/... — closing the asymmetry where an
    intake'd patient was listable but its resource citations 404'd."""
    with TestClient(app) as client:
        intake = client.post(
            "/intake",
            json={
                "connector": "mock-fhir",
                "source_patient_id": "DEMO-001",
                "patient_id": "intake-e2e",
            },
            headers=_HEADERS,
        )
        assert intake.status_code == 201
        assert intake.json()["resource_count"] > 0

        factory = app.state.session_factory

        async def _first_resource():
            async with factory() as session:
                rows = await repo.list_patient_resources(session, patient_id="intake-e2e")
                return rows[0] if rows else None

        row = asyncio.run(_first_resource())
        assert row is not None  # intake persisted at least one FHIR resource

        resp = client.get(
            f"/patients/intake-e2e/resource/{row.resource_type}/{row.resource_id}",
            headers=_HEADERS,
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == row.resource_id


def test_intake_validates_fhir_at_boundary(monkeypatch: pytest.MonkeyPatch):
    """FHIR-01/02: /intake validates each fetched resource against the R4B subset and
    persists only the valid ones; a malformed resource is skipped (never persisted)
    and surfaced as an honest data gap — with no raw PII in the warning (SEC-02)."""
    from datetime import UTC, datetime

    from backend.app.providers.base import FetchResult

    valid_med = {
        "resourceType": "MedicationStatement",
        "id": "med-ok",
        "status": "active",
        "medicationCodeableConcept": {"text": "Aspirin"},
        "subject": {"reference": "Patient/stub-pat"},
    }
    invalid_patient = {
        "resourceType": "Patient",
        "id": "pat-bad",
        "name": [{"family": "Smith", "given": ["Eleanor"]}],
        "gender": 12345,  # must be a code string → fails R4B validation
    }

    class _StubProvider:
        id = "stub-conn"

        async def fetch_patient(self, _source_patient_id: str) -> FetchResult:
            return FetchResult(
                bundle={"entry": [{"resource": valid_med}, {"resource": invalid_patient}]},
                source=self.id,
                fetched_at=datetime.now(UTC),
            )

    monkeypatch.setattr("backend.app.api.intake.build_connector", lambda _name: _StubProvider())

    with TestClient(app) as client:
        intake = client.post(
            "/intake",
            json={"connector": "stub-conn", "source_patient_id": "x", "patient_id": "stub-pat"},
            headers=_HEADERS,
        )
        assert intake.status_code == 201, intake.text
        assert intake.json()["resource_count"] == 1  # only the valid med persisted

        ok_res = client.get(
            "/patients/stub-pat/resource/MedicationStatement/med-ok", headers=_HEADERS
        )
        bad_res = client.get("/patients/stub-pat/resource/Patient/pat-bad", headers=_HEADERS)

        factory = app.state.session_factory

        async def _notice():
            async with factory() as session:
                row = await session.get(CachedResource, ("stub-pat", "FetchMetadata", "stub-pat"))
                return row.body if row is not None else None

        notice = asyncio.run(_notice())

    assert ok_res.status_code == 200  # valid resource is persisted + resolvable
    assert bad_res.status_code == 404  # invalid resource never reached the cache
    assert notice is not None
    warnings = notice["warnings"]
    assert any("Patient/pat-bad" in w for w in warnings)  # surfaced as an honest gap
    # SEC-02: the warning names the type/id + exception class, never the raw PII.
    assert all("Smith" not in w for w in warnings)


def test_intake_pdf_connector_persists_valid_resources_with_span():
    """The pdf connector is reachable via /intake (seeded demo PDF); its
    extracted resources — including R4B-valid Conditions — survive the boundary
    validator, and a span-bearing resource resolves with source_span (the source-PDF
    highlight). Proves both the Condition.subject fix and intake span preservation."""
    with TestClient(app) as client:
        intake = client.post(
            "/intake",
            json={"connector": "pdf", "source_patient_id": "pdf-src", "patient_id": "pdf-intake"},
            headers=_HEADERS,
        )
        assert intake.status_code == 201, intake.text
        # Patient + Conditions + Medications — Conditions are NOT dropped by the validator.
        assert intake.json()["resource_count"] >= 10

        factory = app.state.session_factory

        async def _rows():
            async with factory() as session:
                return await repo.list_patient_resources(session, patient_id="pdf-intake")

        rows = asyncio.run(_rows())
        types = {r.resource_type for r in rows}
        # A non-Patient resource carrying a span (a Patient's span is dropped by the
        # reasoning_view allow-list on read, so pick a Condition/Medication).
        span_row = next(
            (
                r
                for r in rows
                if r.resource_type != "Patient" and isinstance(r.body.get("span"), dict)
            ),
            None,
        )
        assert span_row is not None
        cite = client.get(
            f"/patients/pdf-intake/resource/{span_row.resource_type}/{span_row.resource_id}",
            headers=_HEADERS,
        )

    assert "Condition" in types  # the B.2↔B.3 fix: conditions are now valid + persisted
    assert "MedicationStatement" in types
    assert cite.status_code == 200
    assert "source_span" in cite.json()


def test_intake_hl7v2_connector_persists_patient():
    """The hl7v2 scaffold connector is reachable via /intake (seeded ADT);
    its Patient persists and resolves with no demographic PHI (reasoning_view egress)."""
    with TestClient(app) as client:
        intake = client.post(
            "/intake",
            json={"connector": "hl7v2", "source_patient_id": "x", "patient_id": "hl7-intake"},
            headers=_HEADERS,
        )
        assert intake.status_code == 201, intake.text
        assert intake.json()["resource_count"] == 1
        cite = client.get("/patients/hl7-intake/resource/Patient/PAT001", headers=_HEADERS)
    assert cite.status_code == 200
    body = cite.json()
    assert body["id"] == "PAT001"
    assert "name" not in body  # SEC-02 minimization at egress


def test_institution_connectors_are_registered():
    """The two seeded institutions are reachable as one PostgresProvider with
    different configs (the same provider over two schemas proves generality)."""
    from backend.app.providers import build

    a = build("institution-a")
    b = build("institution-b")
    assert a._institution == "a"
    assert b._institution == "b"


def test_intake_institution_db_unreachable_returns_502(monkeypatch: pytest.MonkeyPatch):
    """An unreachable institution DB degrades gracefully: PostgresProvider raises a
    ConnectorError, which /intake maps to 502 — never a 500."""
    from backend.app.providers.postgres import PostgresProvider

    class _BrokenPool:
        def acquire(self):
            raise OSError("connection refused")

    monkeypatch.setattr(
        "backend.app.api.intake.build_connector",
        lambda _name: PostgresProvider(dsn="postgresql://x", institution="a", pool=_BrokenPool()),
    )
    with TestClient(app) as client:
        resp = client.post(
            "/intake",
            json={"connector": "institution-a", "source_patient_id": "DEMO-001"},
            headers=_HEADERS,
        )
    assert resp.status_code == 502


def test_intake_institution_a_persists_and_resolves_patient(monkeypatch: pytest.MonkeyPatch):
    """An institution-a intake (mock pool, no DB) fetches a Patient through the
    PostgresProvider, passes the boundary validator, persists it, and resolves it as a
    citation — the full flagship integration path, offline."""
    from typing import Any

    from backend.app.providers.postgres import PostgresProvider

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **_: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, *_: Any):
            return {"patient_id": "INST-A-1", "date_of_birth": "1950-03-15", "sex": "F"}

        async def fetch(self, *_: Any) -> list:
            return []

    class _Acquire:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Pool:
        def acquire(self) -> _Acquire:
            return _Acquire()

    monkeypatch.setattr(
        "backend.app.api.intake.build_connector",
        lambda _name: PostgresProvider(dsn="postgresql://x", institution="a", pool=_Pool()),
    )
    with TestClient(app) as client:
        intake = client.post(
            "/intake",
            json={
                "connector": "institution-a",
                "source_patient_id": "INST-A-1",
                "patient_id": "inst-a-intake",
            },
            headers=_HEADERS,
        )
        assert intake.status_code == 201, intake.text
        assert intake.json()["resource_count"] >= 1
        cite = client.get("/patients/inst-a-intake/resource/Patient/INST-A-1", headers=_HEADERS)
    assert cite.status_code == 200
    assert cite.json()["id"] == "INST-A-1"


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
