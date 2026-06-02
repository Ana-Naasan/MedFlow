"""End-to-end tests for partial-data surfacing (#73).

Wiring under test:

  1. /intake calls ``log_partial_fetch`` on the connector's FetchResult and,
     when the notice is non-None, persists it as a CachedResource row keyed by
     ``(patient_id, "FetchMetadata", patient_id)``.
  2. /packet reads that row and folds the notice's ``missing`` categories and
     ``warnings`` into ``DecisionPacket.data_gaps`` at response time.

A fake provider yields controlled ``FetchResult.partial`` / ``warnings`` /
``coverage`` so we can exercise both the complete and partial paths without
hitting a real connector.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.providers.base import (
    Capability,
    FetchResult,
    HealthStatus,
    Provider,
)


@pytest.fixture(autouse=True)
def required_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_GENAI_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("OPENFDA_API_KEY", "PLACEHOLDER")
    monkeypatch.setenv("DEV_TOKEN", "PLACEHOLDER")


_HEADERS = {"Authorization": "Bearer PLACEHOLDER"}


# ── Fake provider ─────────────────────────────────────────────────────────────


class _FakeProvider(Provider):
    """Returns whatever FetchResult was wired in at construction time."""

    id = "fake-partial"
    capabilities = Capability.PATIENT | Capability.MEDICATIONS

    def __init__(self, result: FetchResult) -> None:
        self._result = result

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        return self._result

    async def health_check(self) -> HealthStatus:
        return HealthStatus(ok=True, latency_ms=0.0)


def _bundle(patient_id: str) -> dict[str, object]:
    return {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": patient_id,
                    "identifier": [{"system": "urn:mrn", "value": f"MRN-{patient_id}"}],
                    "gender": "female",
                    "birthDate": "1950-01-01",
                }
            }
        ],
    }


def _partial_result(patient_id: str) -> FetchResult:
    return FetchResult(
        bundle=_bundle(patient_id),
        source="fake-partial",
        fetched_at=datetime.now(UTC),
        partial=True,
        warnings=["Skipped Observation/x: validation failed (KeyError)"],
        coverage={
            "patient": {"requested": True, "returned": True},
            "medications": {"requested": True, "returned": False},
            "observations": {"requested": True, "returned": False},
        },
    )


def _complete_result(patient_id: str) -> FetchResult:
    return FetchResult(
        bundle=_bundle(patient_id),
        source="fake-complete",
        fetched_at=datetime.now(UTC),
        partial=False,
        warnings=[],
        coverage={"patient": {"requested": True, "returned": True}},
    )


def _install_fake_provider(monkeypatch: pytest.MonkeyPatch, result: FetchResult) -> None:
    """Override the connector registry so /intake builds the fake provider."""
    from backend.app.api import intake as intake_mod

    monkeypatch.setattr(intake_mod, "build_connector", lambda _: _FakeProvider(result))


# ── /intake side: persistence ─────────────────────────────────────────────────


def test_intake_with_partial_fetch_persists_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A partial fetch upserts the FetchMetadata row keyed by patient_id."""
    pid = "PARTIAL-001"
    _install_fake_provider(monkeypatch, _partial_result(pid))
    with TestClient(app=_make_app()) as client:
        resp = client.post(
            "/intake",
            json={
                "connector": "ignored",
                "source_patient_id": pid,
                "patient_id": pid,
            },
            headers=_HEADERS,
        )
        assert resp.status_code == 201

        # The notice is folded into /packet's data_gaps at response time:
        pkt = client.get(f"/patients/{pid}/packet", headers=_HEADERS)
        assert pkt.status_code == 200
        gaps = pkt.json()["data_gaps"]
        assert any("medications" in g.lower() for g in gaps), gaps
        assert any("observations" in g.lower() for g in gaps), gaps
        assert any("Skipped Observation/x" in g for g in gaps), gaps


def test_intake_with_complete_fetch_writes_no_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete fetch (no partial, no warnings) leaves data_gaps as the
    packet's own static set — no FetchMetadata row, no merged extras."""
    pid = "COMPLETE-001"
    _install_fake_provider(monkeypatch, _complete_result(pid))
    with TestClient(app=_make_app()) as client:
        intake = client.post(
            "/intake",
            json={
                "connector": "ignored",
                "source_patient_id": pid,
                "patient_id": pid,
            },
            headers=_HEADERS,
        )
        assert intake.status_code == 201

        pkt = client.get(f"/patients/{pid}/packet", headers=_HEADERS)
        assert pkt.status_code == 200
        gaps = pkt.json()["data_gaps"]
        for g in gaps:
            assert "Skipped" not in g
            assert "not returned by source" not in g


def test_partial_notice_merge_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hitting /packet twice never duplicates the merged data_gaps lines."""
    pid = "PARTIAL-002"
    _install_fake_provider(monkeypatch, _partial_result(pid))
    with TestClient(app=_make_app()) as client:
        client.post(
            "/intake",
            json={
                "connector": "ignored",
                "source_patient_id": pid,
                "patient_id": pid,
            },
            headers=_HEADERS,
        )
        first = client.get(f"/patients/{pid}/packet", headers=_HEADERS).json()["data_gaps"]
        second = client.get(f"/patients/{pid}/packet", headers=_HEADERS).json()["data_gaps"]
        assert first == second
        assert len(first) == len(set(first)), "data_gaps must not contain duplicates"


def test_clean_reintake_clears_stale_partial_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    """#91: once a source recovers, a clean re-intake must CLEAR the prior
    partial-data notice so /packet stops surfacing stale 'missing data' gaps.

    Previously the notice was only ever upserted (never deleted), so a patient
    whose source recovered kept showing the old 'missing data' warnings forever.
    """
    pid = "RECOVER-001"
    with TestClient(app=_make_app()) as client:
        # 1. Partial fetch → notice persisted, gaps surface on /packet.
        _install_fake_provider(monkeypatch, _partial_result(pid))
        client.post(
            "/intake",
            json={"connector": "ignored", "source_patient_id": pid, "patient_id": pid},
            headers=_HEADERS,
        )
        gaps_partial = client.get(f"/patients/{pid}/packet", headers=_HEADERS).json()["data_gaps"]
        assert any("Skipped Observation/x" in g for g in gaps_partial), gaps_partial

        # 2. Source recovers → clean re-intake for the SAME patient.
        _install_fake_provider(monkeypatch, _complete_result(pid))
        client.post(
            "/intake",
            json={"connector": "ignored", "source_patient_id": pid, "patient_id": pid},
            headers=_HEADERS,
        )
        gaps_clean = client.get(f"/patients/{pid}/packet", headers=_HEADERS).json()["data_gaps"]

    for g in gaps_clean:
        assert "Skipped" not in g, gaps_clean
        assert "not returned by source" not in g, gaps_clean


# ── /packet side: rendering without prior intake ──────────────────────────────


def test_packet_without_metadata_returns_static_data_gaps_only() -> None:
    """A patient with no FetchMetadata row gets the static packet's data_gaps verbatim."""
    with TestClient(app=_make_app()) as client:
        resp = client.get("/patients/pat-001/packet", headers=_HEADERS)
        assert resp.status_code == 200
        gaps = resp.json()["data_gaps"]
        # The pat-001 static packet ships with "Renal function labs missing" —
        # the merge must leave it untouched and not add any partial-notice lines.
        for g in gaps:
            assert "not returned by source" not in g


# ── SEC-02: warnings-string hygiene (defense-in-depth) ────────────────────────


def test_provider_warnings_never_interpolate_raw_exception_str() -> None:
    """#73 bullet 3 — every site that appends to a `warnings` list must avoid
    raw exception interpolation. Approved sites use only:

      - static strings (pdf.py, mock_fhir "loaded from local snapshot"),
      - identifiers (postgres `event_class`/`event_id`, mock_fhir `rtype/rid`),
      - exception *class name* (e.g. `type(exc).__name__`).

    This guard fires if any new `warnings.append(...)` line interpolates the
    raw `{exc}` / `{err}` / `{e}` value — those carry pydantic
    `input_value=<PHI>` chains and must not cross the logging/notice boundary.
    """
    import pathlib
    import re

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    providers_dir = repo_root / "app" / "providers"
    bad_pattern = re.compile(
        r"warnings\.(append|extend)\([^)]*\{(exc|err|e)\b[^.}]*\}",
    )
    offenders: list[str] = []
    for py in providers_dir.glob("*.py"):
        for lineno, line in enumerate(py.read_text().splitlines(), start=1):
            if bad_pattern.search(line):
                offenders.append(f"{py.name}:{lineno}: {line.strip()}")
    assert (
        not offenders
    ), "SEC-02: raw exception interpolation in a provider warnings string:\n" + "\n".join(offenders)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_app():
    """Build a fresh FastAPI app per test so the in-memory DB doesn't leak.

    backend.app.main.app is module-scoped; in tests where we install a fake
    provider we want a clean DB. Reimporting the app module is the lightest
    way to get a fresh lifespan and a fresh in-memory engine.
    """
    import importlib

    import backend.app.main as main_mod

    importlib.reload(main_mod)
    return main_mod.app
