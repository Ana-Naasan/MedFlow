"""OpenAPI contract tests — the product DTOs must reach the schema (API-08).

Until /packet and /connectors carried a response_model, DecisionPacket / Citation /
Hypothesis / ConnectorStatus were absent from the schema, so the generated typed
clients fell back to untyped `Record<string, unknown>`. These pin them in.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

_REPO_ROOT = Path(__file__).resolve().parents[3]
# The single Umraa frontend keeps its OpenAPI spec + generated client under lib/api/.
_COMMITTED_OPENAPI = "frontend/lib/api/openapi.json"


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


def test_openapi_surfaces_decision_packet_and_nested_dtos() -> None:
    schemas = app.openapi()["components"]["schemas"]
    for name in ["DecisionPacket", "Hypothesis", "Citation", "CategoryCompleteness", "Span"]:
        assert name in schemas, f"{name} missing from OpenAPI components"


def test_packet_endpoint_response_is_typed_as_decision_packet() -> None:
    schema = app.openapi()["paths"]["/patients/{patient_id}/packet"]["get"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]
    assert schema.get("$ref", "").endswith("/DecisionPacket")


def test_openapi_surfaces_connector_status() -> None:
    assert "ConnectorStatus" in app.openapi()["components"]["schemas"]


def test_connectors_endpoint_response_is_typed_as_connector_status_array() -> None:
    schema = app.openapi()["paths"]["/connectors"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema.get("type") == "array"
    assert schema["items"].get("$ref", "").endswith("/ConnectorStatus")


def test_committed_openapi_json_matches_the_live_app() -> None:
    # Drift guard: a backend DTO/route change that skips the regen must fail here
    # (not stay green with a stale committed spec + typed client).
    expected = json.dumps(app.openapi(), indent=2) + "\n"
    committed = (_REPO_ROOT / _COMMITTED_OPENAPI).read_text()
    assert committed == expected, (
        f"{_COMMITTED_OPENAPI} is stale vs the live app.openapi(); regenerate it "
        "(dump app.openapi() with indent=2 + trailing newline), then re-run gen:api in frontend/."
    )


def test_packet_response_still_carries_cache_status_and_data_gaps() -> None:
    # response_model=DecisionPacket must not drop the fields the UI reads.
    with TestClient(app) as client:
        resp = client.get(
            "/patients/pat-001/packet", headers={"Authorization": "Bearer PLACEHOLDER"}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "cache_status" in body
    assert "data_gaps" in body
    assert body["patient_id"] == "pat-001"
