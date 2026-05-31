"""Shared fixtures for backend tests.

OpenFDA tests run fully offline via an ``httpx.MockTransport`` that serves
real-SHAPED openFDA responses (verified against open.fda.gov 2026-05-31):
a normal ``/event`` search returns ``meta.results.total`` + sample records,
a ``count=`` query returns top-level ``{term, count}`` buckets, a
seriousness-filtered search returns ``meta.results.total``, and ``/label``
returns sparse array-of-string section fields. This keeps the connector's real
query/parse paths under test without any network or fabricated ``meta`` shapes.
"""

from __future__ import annotations

import time

import httpx
import pytest

from backend.app.knowledge import openfda

# RxCUI 197885 = lisinopril (the demo drug).
_RXCUI = "197885"

# ── Real-shaped response bodies ──────────────────────────────────────────────

_MAIN_EVENT = {
    "meta": {"disclaimer": "openFDA", "results": {"skip": 0, "limit": 2, "total": 10064}},
    "results": [
        {
            "safetyreportid": "100000001",
            "serious": "1",
            "seriousnessdeath": "1",
            "patient": {
                "drug": [
                    {
                        "medicinalproduct": "LISINOPRIL",
                        "openfda": {
                            "rxcui": ["197885"],
                            "generic_name": ["LISINOPRIL"],
                            "brand_name": ["PRINIVIL"],
                            "manufacturer_name": ["Merck"],
                        },
                    }
                ],
                "reaction": [
                    {"reactionmeddrapt": "COUGH"},
                    {"reactionmeddrapt": "DIZZINESS"},
                ],
            },
        }
    ],
}

# count=patient.reaction.reactionmeddrapt.exact — top-level {term,count} buckets,
# NO meta.results (matches the real count-query envelope).
_COUNT_REACTIONS = {
    "meta": {"disclaimer": "openFDA"},
    "results": [
        {"term": "COUGH", "count": 12000},
        {"term": "DIZZINESS", "count": 9000},
        {"term": "ANGIOEDEMA", "count": 1500},
    ],
}


def _seriousness_total(total: int) -> dict:
    return {"meta": {"results": {"skip": 0, "limit": 1, "total": total}}, "results": [{}]}


_SERIOUSNESS_TOTALS = {
    "seriousnessdeath:1": 42,
    "seriousnesshospitalization:1": 500,
    "serious:1": 1000,
}

_LABEL = {
    "meta": {"results": {"skip": 0, "limit": 1, "total": 1}},
    "results": [
        {
            "boxed_warning": [
                "WARNING: FETAL TOXICITY. Discontinue lisinopril when pregnancy is detected."
            ],
            "warnings": ["Anaphylactoid reactions and angioedema have been reported."],
            "contraindications": ["Do not co-administer aliskiren in patients with diabetes."],
            "indications_and_usage": ["Lisinopril is indicated for the treatment of hypertension."],
            "adverse_reactions": ["Headache, dizziness, and cough were the most common reactions."],
            "openfda": {
                "rxcui": ["197885"],
                "generic_name": ["LISINOPRIL"],
                "brand_name": ["PRINIVIL"],
                "manufacturer_name": ["Merck"],
            },
        }
    ],
}


def _route(search: str, count: str | None, is_label: bool) -> dict:
    """Map a decoded request to the right real-shaped body.

    Seriousness routing requires a REAL space-delimited ``" AND <flag>"`` — the
    form openFDA actually parses. A malformed literal ``"+AND+<flag>"`` (the old
    bug, where httpx percent-encodes the '+') will NOT match here, so it falls
    through to the main event body and the seriousness assertions fail — i.e. the
    mock refuses to mask the encoding bug.
    """
    if is_label:
        return _LABEL
    if count:
        return _COUNT_REACTIONS
    for flag, total in _SERIOUSNESS_TOTALS.items():
        if f" AND {flag}" in search:
            return _seriousness_total(total)
    return _MAIN_EVENT


def _default_handler(request: httpx.Request) -> httpx.Response:
    params = request.url.params
    body = _route(
        params.get("search", ""),
        params.get("count"),
        request.url.path.endswith("/label.json"),
    )
    return httpx.Response(200, json=body)


def _install(monkeypatch, handler) -> None:
    def _mock_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=openfda.BASE_URL, transport=httpx.MockTransport(handler))

    monkeypatch.setattr(openfda, "_client", _mock_client)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_openfda_state() -> None:
    """Clear cache and refill the token bucket before every test (no cross-talk)."""
    openfda._cache.clear()
    openfda._bucket._tokens = float(openfda._bucket._burst)
    openfda._bucket._last = time.monotonic()


@pytest.fixture
def mock_openfda(monkeypatch) -> None:
    """Patch the HTTP client to serve real-shaped fixtures with no network."""
    _install(monkeypatch, _default_handler)


@pytest.fixture
def mock_openfda_factory(monkeypatch):
    """Return an installer so a test can supply its own request handler."""

    def _factory(handler) -> None:
        _install(monkeypatch, handler)

    return _factory
