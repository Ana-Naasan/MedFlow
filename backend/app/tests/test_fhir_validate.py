"""Unit tests for the FHIR R4B boundary validator (FHIR-01/02, SEC-02)."""

from __future__ import annotations

from backend.app.fhir import validate
from backend.app.fhir.validate import validate_fhir_resource


def test_load_validators_loads_and_caches() -> None:
    validate._VALIDATORS = {}
    first = validate._load_validators()
    second = validate._load_validators()
    assert first is second  # cached singleton on the second call
    assert set(first) == {
        "Patient",
        "Condition",
        "MedicationStatement",
        "Observation",
        "AllergyIntolerance",
        "Procedure",
    }


def test_valid_subset_resource_passes() -> None:
    ok, warning = validate_fhir_resource({"resourceType": "Patient", "id": "p1"})
    assert ok is True
    assert warning is None


def test_invalid_subset_resource_is_skipped_without_leaking_pii() -> None:
    bad = {
        "resourceType": "Patient",
        "id": "pat-bad",
        "name": [{"family": "Smith", "given": ["Eleanor"]}],
        "gender": 12345,  # gender must be a code string → real R4B ValidationError
    }
    ok, warning = validate_fhir_resource(bad)
    assert ok is False
    assert warning is not None
    assert "Patient/pat-bad" in warning
    assert "validation failed" in warning
    # SEC-02: the warning carries only the exception class, never the raw error text
    # (which echoes the patient name/address).
    assert "Smith" not in warning
    assert "Eleanor" not in warning


def test_out_of_subset_resource_is_filtered_silently() -> None:
    ok, warning = validate_fhir_resource({"resourceType": "Encounter", "id": "e1"})
    assert ok is False
    assert warning is None  # not an error — just outside the 6-type subset


def test_non_dict_resource_is_skipped() -> None:
    ok, warning = validate_fhir_resource("not-a-dict")
    assert ok is False
    assert warning is not None
    assert "not a FHIR object" in warning


def test_injected_validators_are_used_and_class_only_warning() -> None:
    class _AlwaysInvalid:
        @classmethod
        def model_validate(cls, _d: object) -> object:
            raise ValueError("Smith 742 Evergreen Terrace")

    ok, warning = validate_fhir_resource(
        {"resourceType": "Patient", "id": "p9", "name": [{"family": "Smith"}]},
        _validators={"Patient": _AlwaysInvalid},
    )
    assert ok is False
    assert warning is not None
    assert "Patient/p9" in warning
    assert "ValueError" in warning  # exception class name only
    assert "Smith" not in warning  # SEC-02: raw exception text never interpolated
