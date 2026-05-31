"""Integration: GET /packet runs the REAL reasoning pipeline (only Gemini mocked).

This is the acceptance test the EVAL-REVIEW demands to clear BLOCKER #1 —
run_reasoning is now in the request path, and the served packet's citations
pass verification end-to-end (flatten + verify_citations + verify_packet all
run for real; only the Gemini HTTP call is mocked).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.reasoning.pipeline import REASONED_SUMMARY


@pytest.fixture(autouse=True)
def _secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer PLACEHOLDER"}


def _gemini_returning(payload: dict) -> MagicMock:
    """Build a mock google-genai Client class that returns ``payload`` as JSON."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    mock_aio_models = AsyncMock()
    mock_aio_models.generate_content.return_value = mock_response
    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models
    mock_client = MagicMock()
    mock_client.aio = mock_aio
    mock_genai = MagicMock()
    mock_genai.return_value = mock_client
    return mock_genai


# A hypothesis that cites pat-001's real flattened tag (MedicationStatement/med-001)
# and a real evidence card (ddinter-aspirin-warfarin) — passes both gates.
_VALID_PAYLOAD = {
    "hypotheses": [
        {
            "title": "Aspirin may be associated with bleeding risk",
            "why": "The record lists aspirin; DDInter notes a bleeding-risk interaction.",
            "severity": "moderate",
            "confidence": "low",
            "citations": [
                {"kind": "resource", "ref": "MedicationStatement/med-001", "label": "Aspirin"},
                {"kind": "evidence", "ref": "ddinter-aspirin-warfarin", "label": "DDInter"},
            ],
        }
    ]
}


def test_packet_serves_live_reasoned_hypotheses() -> None:
    with patch("backend.app.reasoning.core.Client", _gemini_returning(_VALID_PAYLOAD)):
        with TestClient(app) as client:
            resp = client.get("/patients/pat-001/packet", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    # Served the LIVE reasoned packet, not the static fallback.
    assert body["summary_markdown"] == REASONED_SUMMARY
    assert len(body["hypotheses"]) == 1
    hyp = body["hypotheses"][0]
    refs = {(c["kind"], c["ref"]) for c in hyp["citations"]}
    assert ("resource", "MedicationStatement/med-001") in refs
    assert ("evidence", "ddinter-aspirin-warfarin") in refs
    # completeness survives the verify_packet rebuild (restored from scaffold).
    assert body["completeness"]


def test_packet_drops_unresolvable_citation_via_real_pipeline() -> None:
    # The model cites a patient resource that is NOT in pat-001's flattened text;
    # the real verify_citations/verify_packet gates drop it → abstain → static.
    forged = {
        "hypotheses": [
            {
                "title": "Forged citation hypothesis",
                "why": "Cites a resource the patient record does not contain.",
                "severity": "high",
                "confidence": "high",
                "citations": [
                    {"kind": "resource", "ref": "MedicationStatement/ghost-999", "label": "Ghost"},
                ],
            }
        ]
    }
    with patch("backend.app.reasoning.core.Client", _gemini_returning(forged)):
        with TestClient(app) as client:
            resp = client.get("/patients/pat-001/packet", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    # Reasoning produced nothing verifiable → static fallback (not the reasoned summary).
    assert body["summary_markdown"] != REASONED_SUMMARY
    assert body["hypotheses"]  # static scaffold is still citation-safe


def test_packet_falls_back_to_static_on_abstention() -> None:
    with patch("backend.app.reasoning.core.Client", _gemini_returning({"hypotheses": []})):
        with TestClient(app) as client:
            resp = client.get("/patients/pat-001/packet", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary_markdown"] != REASONED_SUMMARY
    assert body["hypotheses"]


def test_packet_degrades_to_static_on_blank_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # A present-but-EMPTY GOOGLE_GENAI_API_KEY must NOT 500 — it must degrade to
    # the static scaffold. No Client patch here: the REAL _get_client runs, so
    # this exercises the empty-key path end to end.
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with TestClient(app) as client:
        resp = client.get("/patients/pat-001/packet", headers=_headers())

    assert resp.status_code == 200
    body = resp.json()
    assert body["summary_markdown"] != REASONED_SUMMARY  # served the static fallback
    assert body["hypotheses"]  # pat-001 scaffold citations resolve, so it is served
