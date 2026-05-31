from fastapi.testclient import TestClient

from backend.app.dtos import Citation, DecisionPacket, Hypothesis
from backend.app.main import app


def test_packet_stub_returns_decision_packet():
    client = TestClient(app)
    response = client.get("/packet/pat-001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_id"] == "pat-001"
    assert "summary_markdown" in payload
    assert isinstance(payload["hypotheses"], list)
    assert isinstance(payload["data_gaps"], list)


def test_packet_stub_hypothesis_has_citations():
    client = TestClient(app)
    response = client.get("/packet/pat-001")
    payload = response.json()
    h = payload["hypotheses"][0]
    assert "id" in h
    assert "title" in h
    c = h["citations"][0]
    assert "kind" in c
    assert "ref" in c


def test_dtos_snapshot():
    citation = Citation(kind="evidence_card", ref="rxnorm://1", label=None)
    hypothesis = Hypothesis(
        id="h-1",
        title="t",
        why="w",
        severity="low",
        confidence="high",
        citations=[citation],
    )
    packet = DecisionPacket(
        patient_id="p-1",
        summary_markdown="## stub",
        hypotheses=[hypothesis],
        data_gaps=["missing labs"],
        cache_status=None,
    )
    d = packet.model_dump()
    assert d["patient_id"] == "p-1"
    assert d["hypotheses"][0]["citations"][0]["ref"] == "rxnorm://1"
    assert d["cache_status"] is None
