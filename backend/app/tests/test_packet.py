from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.providers.base import HealthStatus
from backend.app.providers.mock_fhir import MockFHIRProvider
from backend.app.providers.postgres import PostgresProvider


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


def test_confirm_served_packet_hypothesis_succeeds() -> None:
    # Regression (confirm/dismiss 404): the hypothesis id SERVED by /packet must be
    # actionable. Previously the served id ("hyp-001") never matched the namespaced
    # DB key and no row was persisted for the packet-view patient → always 404.
    with TestClient(app) as client:
        pkt = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert pkt.status_code == 200
        served_id = pkt.json()["hypotheses"][0]["id"]
        resp = client.post(
            f"/hypotheses/{served_id}/confirm",
            json={"patient_id": "pat-001"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "confirmed"


def test_dismiss_served_packet_hypothesis_returns_unprefixed_ids() -> None:
    # The dismiss response must echo the SERVED (un-prefixed) hypothesis ids so the
    # provider UI can mark the matching cards dismissed (it keys resolved[hyp.id]).
    with TestClient(app) as client:
        pkt = client.get("/patients/pat-001/packet", headers=_auth_headers())
        served_id = pkt.json()["hypotheses"][0]["id"]
        resp = client.post(
            f"/hypotheses/{served_id}/dismiss",
            json={"patient_id": "pat-001"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "dismissed"
    assert served_id in body["dismissed_ids"]


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
    # The endpoint also surfaces the span under the DTO field name so the
    # highlight view can read it as Citation.source_span (#97).
    assert body["source_span"] == span


def test_demo_packet_pdf_citations_carry_source_span() -> None:
    """End-to-end (#97): the served DEMO-001 packet's PDF resource citations
    carry source_span so the frontend can open the highlight view. The
    abstain_reasoning fixture routes through the verified static scaffold."""
    with TestClient(app) as client:
        resp = client.get("/patients/DEMO-001/packet", headers=_auth_headers())
    assert resp.status_code == 200
    citations = [c for h in resp.json()["hypotheses"] for c in h["citations"]]
    by_ref = {c["ref"]: c for c in citations}

    warfarin = by_ref["MedicationStatement/med-warfarin"]
    assert warfarin["source_span"]["page"] == 2
    assert warfarin["source_span"]["snippet"] == "Warfarin 5 mg oral Anticoagulant Daily"

    # A non-PDF resource citation (the Patient) carries no span → stays null,
    # which the frontend renders as a static, non-interactive chip.
    assert by_ref["Patient/DEMO-001"]["source_span"] is None

    # Evidence (knowledge) citations are never PDF-resource spans.
    assert by_ref["ddinter-warfarin-aspirin"]["source_span"] is None


def test_resource_without_span_has_no_source_span() -> None:
    """A non-PDF resource (no span key) must not gain a source_span (#97)."""
    with TestClient(app) as client:
        resp = client.get(
            "/patients/pat-001/resource/Patient/pat-001",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "span" not in body
    assert "source_span" not in body


def test_db_persisted_resource_resolves_as_citation() -> None:
    """API-02: a resource persisted to the cache (as /intake does for a
    fetched patient) is resolvable via /patients/{id}/resource/... — get_patient_citation
    now falls back to the DB, so an intake'd patient's citations resolve, not just the
    two static seed patients. A span on the persisted body surfaces as source_span."""
    import asyncio

    from backend.app.cache import repo

    pid = "intake-pat-b1"
    persisted = {
        "resourceType": "MedicationStatement",
        "id": "med-intake-1",
        "status": "active",
        "medicationCodeableConcept": {"text": "Lisinopril"},
        "subject": {"reference": f"Patient/{pid}"},
        "span": {"page": 1, "start": 10, "end": 32, "snippet": "Lisinopril 10 mg oral daily"},
    }
    with TestClient(app) as client:

        async def _seed() -> None:
            async with app.state.session_factory() as session:
                async with session.begin():
                    await repo.upsert_resource(
                        session,
                        patient_id=pid,
                        resource_type="MedicationStatement",
                        resource_id="med-intake-1",
                        body=persisted,
                        source_provider="pdf",
                    )

        asyncio.run(_seed())
        resp = client.get(
            f"/patients/{pid}/resource/MedicationStatement/med-intake-1",
            headers=_auth_headers(),
        )
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["id"] == "med-intake-1"
    assert out["medicationCodeableConcept"]["text"] == "Lisinopril"
    # A DB-resolved span-bearing resource surfaces source_span for the highlight view.
    assert out["source_span"]["snippet"] == "Lisinopril 10 mg oral daily"


def test_intake_patient_citation_does_not_leak_demographics() -> None:
    """SEC-02: a DB-resolved Patient citation for an intake'd patient must NOT egress
    name / address / telecom / DOB. Intake persists raw provider bundles, so
    get_patient_citation projects the DB body through the fail-closed reasoning_view —
    only the MRN-keyed minimal demographic set survives (the non-negotiable
    'key on MRN, never name/address/phone' invariant)."""
    import asyncio

    from backend.app.cache import repo

    pid = "intake-phi-1"
    raw_patient = {
        "resourceType": "Patient",
        "id": pid,
        # MR-typed so the fail-closed allow-list retains the MRN we DO keep.
        "identifier": [
            {"type": {"coding": [{"code": "MR"}]}, "system": "urn:mrn", "value": "MRN-PHI-1"}
        ],
        "name": [{"family": "Smith", "given": ["Eleanor"]}],
        "address": [{"city": "Springfield", "line": ["742 Evergreen Terrace"]}],
        "telecom": [{"system": "phone", "value": "555-0100"}],
        "gender": "female",
        "birthDate": "1944-02-18",
    }
    with TestClient(app) as client:

        async def _seed() -> None:
            async with app.state.session_factory() as session:
                async with session.begin():
                    await repo.upsert_resource(
                        session,
                        patient_id=pid,
                        resource_type="Patient",
                        resource_id=pid,
                        body=raw_patient,
                        source_provider="mock-fhir",
                    )

        asyncio.run(_seed())
        resp = client.get(f"/patients/{pid}/resource/Patient/{pid}", headers=_auth_headers())
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["id"] == pid
    # Demographic PHI must be gone.
    assert "name" not in out
    assert "address" not in out
    assert "telecom" not in out
    assert "birthDate" not in out  # reasoning_view derives ageYears instead of DOB
    # The MRN identifier (the key we retain) survives.
    assert out["identifier"][0]["value"] == "MRN-PHI-1"


def test_citation_unknown_to_db_and_static_returns_404_and_is_not_audited() -> None:
    """An id absent from BOTH the DB cache and the static seed store still 404s — the
    DB-first lookup must not mask a genuine miss (nor 500) — and the miss leaves no
    audit row: the unconditional repo.get_resource audit write is rolled back with the
    404, matching the repo's not-found convention (mirrors the /evidence path)."""
    with TestClient(app) as client:
        resp = client.get(
            "/patients/ghost/resource/Patient/ghost",
            headers=_auth_headers(),
        )
        assert resp.status_code == 404
        audit = client.get("/audit", headers=_auth_headers())
    refs = {e["resource_ref"] for e in audit.json()}
    assert "Patient/ghost" not in refs


def test_demo_001_evidence_card_resolves() -> None:
    with TestClient(app) as client:
        resp = client.get("/evidence/ddinter-warfarin-aspirin", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["id"] == "ddinter-warfarin-aspirin"


def test_evidence_db_fallback_resolves_computed_card(monkeypatch: pytest.MonkeyPatch) -> None:
    """API-03: a COMPUTED evidence card persisted on the /packet path
    (and absent from the curated static store) is resolvable via GET /evidence/{id}.

    The endpoint must fall back to the DB-persisted evidence_card store when the
    static store misses, so the provider UI can open a citation chip for a card
    the reasoning core actually produced — not just the hero-demo curated cards."""
    import backend.app.api.packet as packet_mod
    from backend.app.cache.store import get_evidence_card as static_get
    from backend.app.dtos import EvidenceSnippet
    from backend.app.reasoning.knowledge_evidence import KnowledgeEvidence

    card = {
        "id": "openfda-label-lisinopril-computed",
        "source": "openFDA",
        "snippet": "Lisinopril may be associated with cough and dizziness.",
        "ref_url": "https://api.fda.gov/drug/label.json?search=openfda.rxcui:197885",
        "kind": "openfda_label",
    }
    # Premise guard: this id is NOT a curated static card, so a 200 can only come
    # from the DB fallback path (never from the static store).
    assert static_get(card["id"]) is None

    async def _computed(_resources: object, _age_years: object) -> KnowledgeEvidence:
        return KnowledgeEvidence(
            snippets=[
                EvidenceSnippet(
                    id=card["id"], kind=card["kind"], ref=card["id"], label=card["snippet"]
                )
            ],
            cards=[card],
        )

    # Override the autouse offline stub so _build_packet_body persists this card.
    monkeypatch.setattr(packet_mod, "build_knowledge_evidence", _computed)

    with TestClient(app) as client:
        # Serving the packet persists the computed card to the evidence_card store.
        pkt = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert pkt.status_code == 200
        # Absent from the static store → can only resolve via the DB fallback.
        ev = client.get(f"/evidence/{card['id']}", headers=_auth_headers())

    assert ev.status_code == 200, ev.text
    body = ev.json()
    # The served shape must be byte-identical to the static path: the persisted
    # body dict, with the internal 'kind' column never leaking into the response.
    assert body == {
        "id": card["id"],
        "source": card["source"],
        "snippet": card["snippet"],
        "ref_url": card["ref_url"],
    }
    assert "kind" not in body


def test_evidence_db_card_takes_precedence_over_colliding_static_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Provenance: when a computed card shares an id with a curated static
    card, GET /evidence/{id} serves the COMPUTED (DB) body.

    Evidence ids are a global namespace and the computed DDInter id is the sorted
    'ddinter-aspirin-warfarin' — byte-identical to pat-001's curated static card.
    The endpoint must resolve DB-first to match the verifier's precedence
    (_build_packet_body resolves computed-first), so the chip a clinician opens
    shows the SAME evidence the anti-hallucination gate validated, never a divergent
    curated card with the same id."""
    import backend.app.api.packet as packet_mod
    from backend.app.cache.store import get_evidence_card as static_get
    from backend.app.dtos import EvidenceSnippet
    from backend.app.reasoning.knowledge_evidence import KnowledgeEvidence

    collision_id = "ddinter-aspirin-warfarin"
    # Premise: this id IS a curated static card, so a static-first endpoint would
    # serve the wrong body — the test proves the computed DB body wins.
    static = static_get(collision_id)
    assert static is not None
    computed_snippet = "COMPUTED: aspirin + warfarin — major bleeding risk (live DDInter)."
    assert static["snippet"] != computed_snippet

    card = {
        "id": collision_id,
        "source": "DDInter",
        "snippet": computed_snippet,
        "ref_url": "https://ddinter.scbdd.com/",
        "kind": "ddinter_interaction",
    }

    async def _computed(_resources: object, _age_years: object) -> KnowledgeEvidence:
        return KnowledgeEvidence(
            snippets=[
                EvidenceSnippet(
                    id=card["id"], kind=card["kind"], ref=card["id"], label=card["snippet"]
                )
            ],
            cards=[card],
        )

    monkeypatch.setattr(packet_mod, "build_knowledge_evidence", _computed)

    with TestClient(app) as client:
        # Serving the packet persists the computed card under the colliding id.
        pkt = client.get("/patients/pat-001/packet", headers=_auth_headers())
        assert pkt.status_code == 200
        ev = client.get(f"/evidence/{collision_id}", headers=_auth_headers())

    assert ev.status_code == 200, ev.text
    assert ev.json()["snippet"] == computed_snippet  # the gated DB body, not the static one


def test_evidence_read_writes_audit_event() -> None:
    """A resolved evidence read (curated OR computed) is logged (CACHE-03): the
    DB-first lookup runs through repo.get_evidence_card, whose 'evidence_read' audit
    row commits with the 200 response — so curated-card reads are no longer an
    unaudited blind spot."""
    with TestClient(app) as client:
        ev = client.get("/evidence/ddinter-warfarin-aspirin", headers=_auth_headers())
        assert ev.status_code == 200
        audit = client.get("/audit", headers=_auth_headers())
    assert audit.status_code == 200
    refs = {e["resource_ref"] for e in audit.json()}
    assert "evidence/ddinter-warfarin-aspirin" in refs


def test_evidence_unknown_id_returns_404_and_is_not_audited() -> None:
    """An id absent from BOTH stores still 404s — the DB-first lookup must not mask a
    genuine miss (nor 500) — and the miss leaves no audit row: the unconditional repo
    audit write is rolled back with the 404, matching the repo's not-found convention
    (confirm/dismiss likewise skip auditing a not-found)."""
    with TestClient(app) as client:
        resp = client.get("/evidence/no-such-evidence-anywhere", headers=_auth_headers())
        assert resp.status_code == 404
        audit = client.get("/audit", headers=_auth_headers())
    refs = {e["resource_ref"] for e in audit.json()}
    assert "evidence/no-such-evidence-anywhere" not in refs


def test_packet_surfaces_reason07_unresolved_med_gaps(monkeypatch: pytest.MonkeyPatch) -> None:
    """REASON-07 min-input contract: medications that fail to normalize to RxNorm,
    plus a thin overall resolution, are surfaced as explicit data_gaps — so the
    packet never implies confident reasoning over drugs it could not verify."""
    import backend.app.api.packet as packet_mod
    from backend.app.knowledge.rxnav import DrugResolution, DrugResolutionReport
    from backend.app.reasoning.knowledge_evidence import KnowledgeEvidence

    report = DrugResolutionReport(
        resolutions=[
            DrugResolution(
                input_name="Aspirin", rxcui="1191", resolved=True, match_quality="exact"
            ),
            DrugResolution(input_name="Warfarin", resolved=False),  # no RxNorm match
            DrugResolution(
                input_name="Mystery Compound", resolved=False, network_error=True
            ),  # RxNav unavailable
        ]
    )
    # 1/3 resolved < 0.5 threshold → the report carries the thin-input note.
    assert report.low_confidence_note == "limited input — low confidence: only 1/3 drugs resolved"

    async def _thin(_resources: object, _age_years: object) -> KnowledgeEvidence:
        return KnowledgeEvidence(resolution_report=report)

    monkeypatch.setattr(packet_mod, "build_knowledge_evidence", _thin)

    with TestClient(app) as client:
        resp = client.get("/patients/pat-001/packet", headers=_auth_headers())
    assert resp.status_code == 200
    gaps = resp.json()["data_gaps"]
    assert "limited input — low confidence: only 1/3 drugs resolved" in gaps
    # Per-med, distinguishing a genuine "no match" from "RxNav unavailable".
    assert any("Warfarin" in g and "could not be matched to RxNorm" in g for g in gaps)
    assert any("Mystery Compound" in g and "RxNorm lookup unavailable" in g for g in gaps)


def test_packet_no_reason07_noise_when_no_meds_in_report() -> None:
    """The total==0 'no drugs provided' note must NOT leak into data_gaps — a
    no-medications report (what the offline stub yields) is a completeness gap, not
    a low-confidence reasoning signal. Guards against polluting every packet."""
    # Default autouse offline stub returns KnowledgeEvidence() → empty report
    # (total==0, low_confidence_note='...no drugs provided').
    with TestClient(app) as client:
        resp = client.get("/patients/pat-001/packet", headers=_auth_headers())
    assert resp.status_code == 200
    gaps = resp.json()["data_gaps"]
    assert all("low confidence" not in g for g in gaps)
    assert all("no drugs provided" not in g for g in gaps)


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


def test_list_patients_and_refresh() -> None:
    with TestClient(app) as client:
        patients = client.get("/patients", headers=_auth_headers())
        refresh = client.post("/patients/pat-001/refresh", headers=_auth_headers())

    assert patients.status_code == 200
    assert refresh.status_code == 200
    assert refresh.headers["x-cache"] == "REFRESH"


def test_connectors_reports_live_registry_health(monkeypatch: pytest.MonkeyPatch) -> None:
    # Neutralise only the two health checks that do network/DB I/O (mock-fhir → HAPI,
    # postgres → asyncpg) so the probe stays offline and deterministic; pdf/hl7v2
    # health checks are already offline.
    async def _ok(self: object) -> HealthStatus:
        return HealthStatus(ok=True, latency_ms=0.5)

    monkeypatch.setattr(MockFHIRProvider, "health_check", _ok)
    monkeypatch.setattr(PostgresProvider, "health_check", _ok)

    with TestClient(app) as client:
        resp = client.get("/connectors", headers=_auth_headers())

    assert resp.status_code == 200
    body = resp.json()
    # Live registry: all five registered connectors self-advertise. The old static
    # list returned only mock-fhir + a "postgres" name that was never registered.
    assert [c["id"] for c in body] == [
        "mock-fhir",
        "pdf",
        "hl7v2",
        "institution-a",
        "institution-b",
    ]
    for connector in body:
        # Slim contract — and never leak raw health detail (SEC-02).
        assert set(connector) == {"id", "name", "capabilities", "health", "latency_ms"}
        assert connector["health"] in {"ok", "down"}
        assert isinstance(connector["capabilities"], list)


def test_packet_cache_miss_race_returns_a_valid_empty_packet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A lost refresh race with an empty cache yields (None, MISS). The body must
    # still be a valid DecisionPacket (response_model would 500 on a bare dict),
    # served with X-Cache: MISS so the client retries.
    from backend.app.cache import repo as cache_repo
    from backend.app.cache.repo import CacheStatus

    async def _miss(*args: object, **kwargs: object):
        return None, CacheStatus.MISS

    monkeypatch.setattr(cache_repo, "get_or_refresh", _miss)
    with TestClient(app) as client:
        resp = client.get("/patients/pat-001/packet", headers=_auth_headers())

    assert resp.status_code == 200
    assert resp.headers["x-cache"] == "MISS"
    body = resp.json()
    assert body["patient_id"] == "pat-001"
    assert body["cache_status"] == "MISS"
    assert body["hypotheses"] == []


def test_audited_reads_attribute_the_token_subject_not_a_placeholder() -> None:
    # API-07: every audited action must record the authenticated token subject,
    # not the old hardcoded actor="api" placeholder.
    from backend.app.api.auth import dev_token_subject

    expected = dev_token_subject("PLACEHOLDER")
    with TestClient(app) as client:
        client.get("/patients/pat-001/packet", headers=_auth_headers())
        client.get("/patients/pat-001/resource/Patient/pat-001", headers=_auth_headers())
        client.get("/evidence/openfda-label-amitriptyline", headers=_auth_headers())
        audit = client.get("/audit", headers=_auth_headers())

    actors = {e["actor"] for e in audit.json()}
    assert actors == {expected}  # packet read + resource read + evidence read all attributed
    assert "api" not in actors


def test_refresh_writes_an_audit_event_with_the_token_subject() -> None:
    # A forced refresh re-pulls + overwrites a patient's packet — an authenticated
    # action that must leave an audit trail, attributed to the token subject.
    from backend.app.api.auth import dev_token_subject

    expected = dev_token_subject("PLACEHOLDER")
    with TestClient(app) as client:
        refreshed = client.post("/patients/pat-001/refresh", headers=_auth_headers())
        assert refreshed.status_code == 200
        audit = client.get("/audit", headers=_auth_headers())

    refresh_events = [
        e
        for e in audit.json()
        if e["resource_ref"] == "DecisionPacket/pat-001" and e["event_type"] == "resource_read"
    ]
    assert refresh_events, "POST /refresh wrote no audit event"
    assert all(e["actor"] == expected for e in refresh_events)


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


def test_wrong_bearer_token_is_rejected() -> None:
    # Contract guard for the constant-time token check: an INCORRECT token must be
    # rejected with 401 (the comparison uses secrets.compare_digest to avoid a
    # token-guessing timing side-channel).
    with TestClient(app) as client:
        resp = client.get("/audit?limit=10", headers={"Authorization": "Bearer WRONG-TOKEN"})
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
