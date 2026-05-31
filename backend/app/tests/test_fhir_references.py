"""Tests for backend/app/fhir/references.py — resolve_references()."""

import copy

import pytest

from backend.app.fhir.references import resolve_references

_RAW = {
    "resourceType": "Observation",
    "id": "obs-1",
    "subject": {"reference": "urn:uuid:abc-123"},
    "code": {"coding": [{"code": "x"}]},
    "contained": [
        {
            "resourceType": "Condition",
            "id": "c1",
            "subject": {"reference": "urn:uuid:abc-123"},
            "asserter": {"reference": "urn:uuid:unknown"},
        }
    ],
    "performer": [
        {"reference": "urn:uuid:def-456"},
        {"reference": "urn:uuid:abc-123"},
    ],
}

_ID_MAP: dict[str, str] = {
    "urn:uuid:abc-123": "Patient/p1",
    "urn:uuid:def-456": "Condition/c1",
}


class TestResolveReferences:
    def test_rewrites_subject_reference(self):
        resolved = resolve_references(_RAW, _ID_MAP)
        assert resolved["subject"]["reference"] == "Patient/p1"

    def test_rewrites_deeply_nested_reference(self):
        resolved = resolve_references(_RAW, _ID_MAP)
        assert resolved["contained"][0]["subject"]["reference"] == "Patient/p1"

    def test_leaves_unmatched_uuid_untouched(self):
        resolved = resolve_references(_RAW, _ID_MAP)
        assert resolved["contained"][0]["asserter"]["reference"] == "urn:uuid:unknown"

    def test_rewrites_multiple_references_in_list(self):
        resolved = resolve_references(_RAW, _ID_MAP)
        assert resolved["performer"][0]["reference"] == "Condition/c1"
        assert resolved["performer"][1]["reference"] == "Patient/p1"

    def test_empty_id_map_fast_path(self):
        assert resolve_references(_RAW, {}) is _RAW

    def test_no_side_effects_on_input(self):
        original = copy.deepcopy(_RAW)
        _ = resolve_references(_RAW, _ID_MAP)
        assert _RAW == original

    def test_non_dict_input_passthrough(self):
        assert resolve_references(None, _ID_MAP) is None
        assert resolve_references("hello", _ID_MAP) == "hello"
        assert resolve_references(42, _ID_MAP) == 42

    def test_reference_not_in_a_reference_field_is_rewritten(self):
        """Any dict key called 'reference' gets rewritten — even if the
        enclosing object isn't a FHIR Reference.  This is intentional:
        Synthea sometimes embeds urn:uuid in unexpected places."""
        data = {"someContainer": {"reference": "urn:uuid:abc-123"}}
        resolved = resolve_references(data, _ID_MAP)
        assert resolved["someContainer"]["reference"] == "Patient/p1"
