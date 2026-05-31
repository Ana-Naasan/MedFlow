from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.app.providers.mock_fhir as _mod
from backend.app.providers.base import ConnectorDataError, ConnectorUnavailable, FetchResult
from backend.app.providers.mock_fhir import (
    _KEPT_TYPES,
    MockFHIRProvider,
    _fetch_raw_entries,
    _load_validators,
    _save_snapshot,
    _trim_and_validate,
)

# ── shared fakes ─────────────────────────────────────────────────────────────


class _Res:
    """Minimal fhirpy resource stand-in."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def serialize(self) -> dict:
        return self._data


class _SearchSet:
    """Chainable mock for client.resources(t).search(**kw).first()/.fetch()."""

    def __init__(self, *, first=None, items=None, raise_exc: Exception | None = None) -> None:
        self._first = first
        self._items = items or []
        self._exc = raise_exc

    def search(self, **_kwargs) -> _SearchSet:
        return self

    async def first(self):
        if self._exc:
            raise self._exc
        return self._first

    async def fetch(self):
        if self._exc:
            raise self._exc
        return self._items


class _FHIRClient:
    """Mock fhirpy client with per-type data."""

    def __init__(self, *, patient=None, by_type=None, exc: Exception | None = None) -> None:
        self._patient = patient
        self._by_type = by_type or {}
        self._exc = exc

    def resources(self, rtype: str) -> _SearchSet:
        if self._exc:
            raise self._exc
        if rtype == "Patient":
            return _SearchSet(first=self._patient)
        return _SearchSet(items=self._by_type.get(rtype, []))


class _PassThrough:
    """Stand-in for fhir.resources model — identity transform."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw

    @classmethod
    def model_validate(cls, raw: dict) -> _PassThrough:
        return cls(raw)

    def model_dump(self, **_kwargs) -> dict:
        return self._raw


_STUB_VALIDATORS = {t: _PassThrough for t in _KEPT_TYPES}

# ── _load_validators ──────────────────────────────────────────────────────────

_FHIR_SUBMODULES = [
    "fhir",
    "fhir.resources",
    "fhir.resources.R4B",
    "fhir.resources.R4B.allergyintolerance",
    "fhir.resources.R4B.condition",
    "fhir.resources.R4B.medicationstatement",
    "fhir.resources.R4B.observation",
    "fhir.resources.R4B.patient",
    "fhir.resources.R4B.procedure",
]


def _inject_fhir_mocks():
    """Inject stub fhir.resources submodules; return a dict of (key → original) for cleanup."""
    saved = {}
    for path in _FHIR_SUBMODULES:
        saved[path] = sys.modules.get(path, _SENTINEL)
        sys.modules[path] = MagicMock()
    # Give each leaf module the correct class attribute name
    for path in _FHIR_SUBMODULES[3:]:  # leaf modules only
        class_name = path.rsplit(".", 1)[-1].title().replace("_", "")
        # e.g. allergyintolerance → Allergyintolerance; fix capitalisation
        corrections = {
            "Allergyintolerance": "AllergyIntolerance",
            "Medicationstatement": "MedicationStatement",
        }
        class_name = corrections.get(class_name, class_name)
        setattr(sys.modules[path], class_name, MagicMock())
    return saved


def _restore_fhir_mocks(saved: dict):
    for path, original in saved.items():
        if original is _SENTINEL:
            sys.modules.pop(path, None)
        else:
            sys.modules[path] = original


def test_load_validators_returns_all_six_types():
    saved_validators = _mod._VALIDATORS.copy()
    _mod._VALIDATORS = {}
    saved_mods = _inject_fhir_mocks()
    try:
        v = _load_validators()
        assert set(v.keys()) == _KEPT_TYPES
    finally:
        _mod._VALIDATORS = saved_validators
        _restore_fhir_mocks(saved_mods)


def test_load_validators_returns_cached_on_second_call():
    """When _VALIDATORS is already populated the early-return path is taken."""
    fake = {t: MagicMock() for t in _KEPT_TYPES}
    saved = _mod._VALIDATORS.copy()
    _mod._VALIDATORS = fake
    try:
        result = _load_validators()
        assert result is fake
    finally:
        _mod._VALIDATORS = saved


# ── _trim_and_validate ────────────────────────────────────────────────────────


def test_trim_keeps_only_six_types():
    """Resources outside our 6 types are dropped; known types pass through."""
    entries = [
        {"resource": {"resourceType": "Patient", "id": "p1", "gender": "male"}},
        {"resource": {"resourceType": "Encounter", "id": "enc-1", "status": "finished"}},
        {"resource": {"resourceType": "Claim", "id": "claim-1", "status": "active"}},
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-1",
                "subject": {"reference": "Patient/p1"},
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "73211009",
                            "display": "DM",
                        }
                    ]
                },
            }
        },
        {"resource": {"resourceType": "MedicationStatement", "id": "med-1"}},
        {"resource": {"resourceType": "Observation", "id": "obs-1"}},
        {"resource": {"resourceType": "AllergyIntolerance", "id": "ai-1"}},
        {"resource": {"resourceType": "Procedure", "id": "proc-1"}},
    ]

    validated, warnings = _trim_and_validate(entries, _validators=_STUB_VALIDATORS)

    returned_types = {r.get("resourceType") for r in validated}

    assert "Encounter" not in returned_types, "Encounter must be filtered out"
    assert "Claim" not in returned_types, "Claim must be filtered out"
    assert returned_types.issubset(_KEPT_TYPES), f"Unexpected types: {returned_types - _KEPT_TYPES}"
    assert "Patient" in returned_types
    assert "Condition" in returned_types


def test_trim_skips_non_dict_resource():
    """Entries whose 'resource' value is not a dict are silently ignored."""
    entries = [
        {"resource": "not-a-dict"},
        {"resource": None},
        {"resource": 42},
    ]
    validated, warnings = _trim_and_validate(entries, _validators=_STUB_VALIDATORS)
    assert validated == []
    assert warnings == []


def test_trim_invalid_resource_emits_warning():
    """A resource that fails model_validate is skipped with a warning."""

    class _AlwaysFails:
        @classmethod
        def model_validate(cls, raw):
            raise ValueError("invalid")

    bad_validators = {"Patient": _AlwaysFails}
    entries = [{"resource": {"resourceType": "Patient", "id": "p1"}}]

    validated, warnings = _trim_and_validate(entries, _validators=bad_validators)

    assert validated == []
    assert any("Patient/p1" in w for w in warnings)


# ── _save_snapshot ────────────────────────────────────────────────────────────


def test_save_snapshot_creates_file(tmp_path: Path):
    bundle = {"resourceType": "Bundle", "entry": []}
    path = tmp_path / "sub" / "snap.json"
    _save_snapshot(path, bundle)
    assert path.exists()
    assert json.loads(path.read_text()) == bundle


# ── _fetch_raw_entries ────────────────────────────────────────────────────────


def test_fetch_raw_entries_includes_patient_when_found():
    patient_data = {"resourceType": "Patient", "id": "p1"}
    client = _FHIRClient(patient=_Res(patient_data))
    entries = asyncio.run(_fetch_raw_entries(client, "p1"))
    assert any(e["resource"]["resourceType"] == "Patient" for e in entries)


def test_fetch_raw_entries_omits_patient_when_none():
    client = _FHIRClient(patient=None)
    entries = asyncio.run(_fetch_raw_entries(client, "p1"))
    assert not any(e["resource"]["resourceType"] == "Patient" for e in entries)


def test_fetch_raw_entries_includes_related_resources():
    client = _FHIRClient(
        patient=None,
        by_type={
            "Condition": [_Res({"resourceType": "Condition", "id": "c1"})],
            "AllergyIntolerance": [_Res({"resourceType": "AllergyIntolerance", "id": "a1"})],
        },
    )
    entries = asyncio.run(_fetch_raw_entries(client, "p1"))
    types = {e["resource"]["resourceType"] for e in entries}
    assert "Condition" in types
    assert "AllergyIntolerance" in types


def test_fetch_raw_entries_swallows_all_exceptions():
    """When the client raises for every resource type, the result is an empty list."""
    client = _FHIRClient(exc=RuntimeError("network failure"))
    entries = asyncio.run(_fetch_raw_entries(client, "p1"))
    assert entries == []


# ── fetch_patient dispatch ────────────────────────────────────────────────────


def test_fetch_patient_reads_from_snapshot(tmp_path: Path):
    """Provider returns the pre-saved bundle when the snapshot file exists (no network)."""
    snap_bundle = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-example",
                    "gender": "male",
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "cond-001",
                    "subject": {"reference": "Patient/patient-example"},
                }
            },
        ],
    }
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(snap_bundle))

    provider = MockFHIRProvider(snapshot_path=snap)
    result = asyncio.run(provider.fetch_patient("patient-example"))

    assert result.bundle["resourceType"] == "Bundle"
    resource_types = {e["resource"]["resourceType"] for e in result.bundle["entry"]}
    assert "Patient" in resource_types
    assert result.source == "mock-fhir"
    assert any("snapshot" in w.lower() for w in result.warnings)
    assert result.coverage["patient"]["returned"] is True
    assert result.coverage["conditions"]["returned"] is True


def test_fetch_patient_delegates_to_live_when_no_snapshot(tmp_path: Path):
    """fetch_patient calls _fetch_live when the snapshot does not exist."""
    snap = tmp_path / "snap.json"
    provider = MockFHIRProvider(snapshot_path=snap)

    dummy = FetchResult(
        bundle={"resourceType": "Bundle", "entry": []},
        source="mock-fhir",
        fetched_at=datetime.now(UTC),
    )
    with patch.object(provider, "_fetch_live", new=AsyncMock(return_value=dummy)):
        result = asyncio.run(provider.fetch_patient("p1"))

    assert result is dummy


# ── health_check ──────────────────────────────────────────────────────────────


def _mock_httpx(status_code: int | None = 200, raise_exc: Exception | None = None):
    """Return a context-manager mock for httpx.AsyncClient."""
    mock_cls = MagicMock()
    if raise_exc:
        mock_cls.return_value.__aenter__ = AsyncMock(side_effect=raise_exc)
    else:
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=MagicMock(status_code=status_code))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_http)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_cls


def test_health_check_ok():
    with patch("backend.app.providers.mock_fhir.httpx.AsyncClient", _mock_httpx(200)):
        result = asyncio.run(MockFHIRProvider().health_check())
    assert result.ok is True
    assert result.latency_ms >= 0
    assert result.detail is None


def test_health_check_server_error():
    with patch("backend.app.providers.mock_fhir.httpx.AsyncClient", _mock_httpx(503)):
        result = asyncio.run(MockFHIRProvider().health_check())
    assert result.ok is False
    assert "503" in result.detail


def test_health_check_network_failure():
    with patch(
        "backend.app.providers.mock_fhir.httpx.AsyncClient",
        _mock_httpx(raise_exc=RuntimeError("unreachable")),
    ):
        result = asyncio.run(MockFHIRProvider().health_check())
    assert result.ok is False
    assert result.detail is not None


# ── _fetch_live ───────────────────────────────────────────────────────────────

_SENTINEL = object()


def _block_fhirpy():
    """Return a context-manager that makes 'from fhirpy import ...' raise ImportError."""

    class _Ctx:
        def __enter__(self):
            self._saved = sys.modules.pop("fhirpy", _SENTINEL)
            sys.modules["fhirpy"] = None
            return self

        def __exit__(self, *_):
            del sys.modules["fhirpy"]
            if self._saved is not _SENTINEL:
                sys.modules["fhirpy"] = self._saved

    return _Ctx()


def _inject_fhirpy(client):
    """Return a context-manager that injects a mock fhirpy.AsyncFHIRClient."""

    class _Ctx:
        def __enter__(self):
            mock = MagicMock()
            mock.AsyncFHIRClient.return_value = client
            self._saved = sys.modules.pop("fhirpy", _SENTINEL)
            sys.modules["fhirpy"] = mock
            return self

        def __exit__(self, *_):
            del sys.modules["fhirpy"]
            if self._saved is not _SENTINEL:
                sys.modules["fhirpy"] = self._saved

    return _Ctx()


def test_fetch_live_raises_when_fhirpy_missing(tmp_path: Path):
    snap = tmp_path / "snap.json"
    provider = MockFHIRProvider(snapshot_path=snap)
    with _block_fhirpy():
        with pytest.raises(ConnectorDataError, match="fhirpy"):
            asyncio.run(provider._fetch_live("p1"))


def test_fetch_live_raises_connector_unavailable_when_client_errors(tmp_path: Path):
    snap = tmp_path / "snap.json"
    provider = MockFHIRProvider(snapshot_path=snap)
    broken_client_factory = MagicMock(side_effect=RuntimeError("cannot connect"))

    class _BrokenFhirpy:
        AsyncFHIRClient = broken_client_factory

    saved = sys.modules.pop("fhirpy", _SENTINEL)
    sys.modules["fhirpy"] = _BrokenFhirpy()
    try:
        with pytest.raises(ConnectorUnavailable, match="unreachable"):
            asyncio.run(provider._fetch_live("p1"))
    finally:
        del sys.modules["fhirpy"]
        if saved is not _SENTINEL:
            sys.modules["fhirpy"] = saved


def test_fetch_live_saves_snapshot_and_returns_result(tmp_path: Path):
    snap = tmp_path / "snap.json"
    provider = MockFHIRProvider(snapshot_path=snap)

    mock_client = _FHIRClient(patient=_Res({"resourceType": "Patient", "id": "p1"}))

    with _inject_fhirpy(mock_client):
        with patch(
            "backend.app.providers.mock_fhir._trim_and_validate",
            return_value=([{"resourceType": "Patient", "id": "p1"}], []),
        ):
            result = asyncio.run(provider._fetch_live("p1"))

    assert snap.exists(), "snapshot must be written after live fetch"
    assert result.source == "mock-fhir"
    assert result.coverage["patient"]["returned"] is True


# ── _load_snapshot error path ─────────────────────────────────────────────────


def test_load_snapshot_raises_on_corrupt_file(tmp_path: Path):
    snap = tmp_path / "snap.json"
    snap.write_text("not valid json{{{")
    provider = MockFHIRProvider(snapshot_path=snap)
    with pytest.raises(ConnectorDataError, match="Cannot read snapshot"):
        provider._load_snapshot("p1")
