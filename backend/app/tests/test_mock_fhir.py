from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from backend.app.providers.mock_fhir import MockFHIRProvider, _KEPT_TYPES, _trim_and_validate


# ── helpers ──────────────────────────────────────────────────────────────────


class _PassThrough:
    """Minimal stand-in for a fhir.resources model — returns the raw dict unchanged."""

    def __init__(self, raw: dict) -> None:
        self._raw = raw

    @classmethod
    def model_validate(cls, raw: dict) -> "_PassThrough":
        return cls(raw)

    def model_dump(self, **_kwargs) -> dict:
        return self._raw


_STUB_VALIDATORS = {t: _PassThrough for t in _KEPT_TYPES}


# ── test 1: shape → 6 types ───────────────────────────────────────────────────


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


# ── test 2: reads from the saved snapshot ────────────────────────────────────


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
    # coverage should reflect what's in the bundle
    assert result.coverage["patient"]["returned"] is True
    assert result.coverage["conditions"]["returned"] is True
