"""Tests for the FHIR subset builders (backend/app/fhir/subset.py).

Covers:
  - Successful construction + round-trip for every builder
  - Loud failure on poor input (wrong types, bad formats, empty required fields)
"""

import copy
import datetime

import pytest
from pydantic import ValidationError

from backend.app.fhir.subset import (
    build_allergy_intolerance,
    build_condition,
    build_medication_statement,
    build_observation,
    build_patient,
    build_procedure,
    reasoning_view,
)

# ── Helpers ────────────────────────────────────────────────────────────────


def _valid_kwargs(builder_name: str) -> dict:
    """Return a minimal set of valid keyword arguments for the given builder."""
    pool: dict[str, dict] = {
        "build_patient": dict(
            id="p1",
            mrn="MRN001",
            family_name="Smith",
            given_name="John",
            gender="male",
            birth_date="1990-01-15",
        ),
        "build_condition": dict(
            id="c1",
            subject_ref="Patient/p1",
            code_system="http://snomed.info/sct",
            code="38341003",
            display="Hypertension",
        ),
        "build_observation": dict(
            id="o1",
            subject_ref="Patient/p1",
            loinc_code="8480-6",
            loinc_display="Systolic BP",
            value=120,
            unit="mmHg",
            unit_code="mm[Hg]",
        ),
        "build_medication_statement": dict(
            id="ms1",
            subject_ref="Patient/p1",
            rxnorm_code="312961",
            rxnorm_display="Lisinopril 10 MG",
        ),
        "build_allergy_intolerance": dict(
            id="a1",
            patient_ref="Patient/p1",
            code="91936005",
            display="Allergy to penicillin",
        ),
        "build_procedure": dict(
            id="pr1",
            subject_ref="Patient/p1",
            code="80146002",
            display="Appendectomy",
            performed_date_time="2024-06-15T10:30:00Z",
        ),
    }
    return pool[builder_name]


def _assert_round_trip(model):
    """Assert that a model survives a dict → model → dict round-trip unchanged."""
    dumped = model.model_dump()
    reloaded = model.__class__.model_validate(dumped)
    assert reloaded.model_dump() == dumped


# ── Successful construction + round-trip ───────────────────────────────────


class TestBuildSuccess:
    def test_build_patient(self):
        model = build_patient(**_valid_kwargs("build_patient"))
        _assert_round_trip(model)

    def test_build_condition(self):
        model = build_condition(**_valid_kwargs("build_condition"))
        _assert_round_trip(model)

    def test_build_observation(self):
        model = build_observation(**_valid_kwargs("build_observation"))
        _assert_round_trip(model)

    def test_build_medication_statement(self):
        model = build_medication_statement(**_valid_kwargs("build_medication_statement"))
        _assert_round_trip(model)

    def test_build_allergy_intolerance(self):
        model = build_allergy_intolerance(**_valid_kwargs("build_allergy_intolerance"))
        _assert_round_trip(model)

    def test_build_procedure(self):
        model = build_procedure(**_valid_kwargs("build_procedure"))
        _assert_round_trip(model)


# ── Extra fields / defaults ────────────────────────────────────────────────


class TestBuildDefaults:
    """Verify that optional parameters and defaults produce valid models."""

    def test_patient_birth_date_parsed_to_date(self):
        p = build_patient(**_valid_kwargs("build_patient"))
        d = p.model_dump()
        assert isinstance(d["birthDate"], datetime.date)

    def test_patient_mrn_present(self):
        p = build_patient(**_valid_kwargs("build_patient"))
        d = p.model_dump()
        identifiers = d.get("identifier", [])
        mrn_values = [
            idv["value"]
            for idv in identifiers
            if idv.get("type", {}).get("coding", [{}])[0].get("code") == "MR"
        ]
        assert mrn_values == ["MRN001"]

    def test_observation_no_value(self):
        kw = _valid_kwargs("build_observation")
        kw["value"] = None
        obs = build_observation(**kw)
        d = obs.model_dump()
        assert d.get("valueQuantity") is None

    def test_procedure_no_performed_date(self):
        kw = _valid_kwargs("build_procedure")
        kw["performed_date_time"] = None
        proc = build_procedure(**kw)
        d = proc.model_dump()
        assert d.get("performedDateTime") is None


# ── Loud failure on poor input ─────────────────────────────────────────────


class TestBuildFailure:
    """Every builder must raise ValidationError on bad input."""

    # ── Wrong types ────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "builder, kwargs",
        [
            ("build_patient", dict(id=123)),
            ("build_condition", dict(subject_ref=42)),
            ("build_observation", dict(loinc_code=True)),
            ("build_medication_statement", dict(rxnorm_code=123)),  # int where str expected
            ("build_allergy_intolerance", dict(code=[])),
            ("build_procedure", dict(status=999)),
        ],
        ids=lambda v: str(v)[:40],
    )
    def test_wrong_types(self, builder, kwargs):
        fn = globals()[builder]
        base = _valid_kwargs(builder)
        base.update(kwargs)
        with pytest.raises(ValidationError):
            fn(**base)

    # ── Bad date formats (caught by round-trip) ────────────────────────

    @pytest.mark.parametrize(
        "builder, field, bad_value",
        [
            ("build_patient", "birth_date", "not-a-date"),
            ("build_procedure", "performed_date_time", "never"),
        ],
    )
    def test_bad_date_format(self, builder, field, bad_value):
        fn = globals()[builder]
        base = _valid_kwargs(builder)
        base[field] = bad_value
        with pytest.raises(ValidationError):
            fn(**base)

    # ── Empty / missing required strings ───────────────────────────────

    @pytest.mark.parametrize(
        "builder, field",
        [
            ("build_patient", "id"),
            ("build_patient", "mrn"),
            ("build_patient", "family_name"),
            ("build_patient", "given_name"),
            ("build_condition", "id"),
            ("build_condition", "subject_ref"),
            ("build_observation", "id"),
            ("build_observation", "loinc_code"),
            ("build_medication_statement", "id"),
            ("build_medication_statement", "rxnorm_code"),
            ("build_allergy_intolerance", "id"),
            ("build_allergy_intolerance", "patient_ref"),
            ("build_procedure", "id"),
            ("build_procedure", "code"),
        ],
    )
    def test_empty_required_string(self, builder, field):
        fn = globals()[builder]
        base = _valid_kwargs(builder)
        base[field] = ""
        with pytest.raises(ValidationError):
            fn(**base)

    # ── Missing required keyword (no default) ──────────────────────────

    @pytest.mark.parametrize(
        "builder, missing_field",
        [
            ("build_patient", "id"),
            ("build_condition", "code_system"),
            ("build_observation", "loinc_display"),
            ("build_medication_statement", "rxnorm_display"),
            ("build_allergy_intolerance", "code"),
            ("build_procedure", "display"),
        ],
    )
    def test_missing_required(self, builder, missing_field):
        fn = globals()[builder]
        base = _valid_kwargs(builder)
        del base[missing_field]
        with pytest.raises(TypeError):  # missing keyword → TypeError from Python
            fn(**base)


# ── Reasoning view ─────────────────────────────────────────────────────────


class TestReasoningView:
    def test_strips_patient_name(self):
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"family": "Smith", "given": ["John"]}],
            "birthDate": "1990-01-15",
            "gender": "male",
            "identifier": [
                {
                    "value": "MRN001",
                    "type": {"coding": [{"code": "MR"}]},
                }
            ],
        }
        view = reasoning_view(raw)
        assert "name" not in view

    def test_strips_address(self):
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "address": [{"city": "Boston"}],
            "birthDate": "1990-01-15",
        }
        view = reasoning_view(raw)
        assert "address" not in view

    def test_strips_telecom(self):
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "telecom": [{"system": "phone", "value": "555-0100"}],
            "birthDate": "1990-01-15",
        }
        view = reasoning_view(raw)
        assert "telecom" not in view

    def test_strips_contact(self):
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "contact": [{"name": {"family": "Jones"}}],
            "birthDate": "1990-01-15",
        }
        view = reasoning_view(raw)
        assert "contact" not in view

    def test_birth_date_replaced_by_age_years(self):
        """birthDate is removed and ageYears is computed from it."""
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"family": "Smith"}],
            "birthDate": "1990-01-15",
        }
        view = reasoning_view(raw)
        assert "birthDate" not in view
        assert isinstance(view.get("ageYears"), int)
        assert view["ageYears"] >= 35  # 1990 → 2026 is 36

    def test_mrn_identifiers_kept(self):
        """Only MRN-type identifiers survive filtering."""
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"family": "Smith"}],
            "birthDate": "1990-01-15",
            "identifier": [
                {
                    "value": "MRN001",
                    "type": {"coding": [{"code": "MR"}]},
                },
                {
                    "value": "SSN123",
                    "type": {"coding": [{"code": "SS"}]},
                },
                {
                    "value": "DL456",
                    "type": {"coding": [{"code": "DL"}]},
                },
            ],
        }
        view = reasoning_view(raw)
        assert len(view["identifier"]) == 1
        assert view["identifier"][0]["value"] == "MRN001"

    def test_non_patient_resource_passes_through_unchanged(self):
        raw = {
            "resourceType": "Condition",
            "id": "c1",
            "code": {"coding": [{"code": "38341003"}]},
            "subject": {"reference": "Patient/p1"},
        }
        view = reasoning_view(raw)
        assert view == raw

    def test_no_mutation_of_input(self):
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"family": "Smith"}],
            "birthDate": "1990-01-15",
        }
        original = copy.deepcopy(raw)
        _ = reasoning_view(raw)
        assert raw == original

    def test_strips_nested_pii_under_contained(self):
        """PII keys nested anywhere in the tree are stripped.
        Contained Patient resources also get birthDate → ageYears
        minimisation."""
        raw = {
            "resourceType": "Observation",
            "id": "o1",
            "contained": [
                {
                    "resourceType": "Patient",
                    "id": "p-contained",
                    "name": [{"family": "Secret"}],
                    "birthDate": "1980-05-10",
                    "address": [{"city": "Hidden"}],
                }
            ],
            "subject": {"reference": "Patient/p1"},
        }
        view = reasoning_view(raw)
        contained = view["contained"][0]
        assert "name" not in contained
        assert "address" not in contained
        assert "birthDate" not in contained
        assert contained["ageYears"] >= 44  # 1980 → 2026 is 46

    def test_reasoning_view_from_built_patient(self):
        """Integration: build_patient → model_dump → reasoning_view."""
        p = build_patient(**_valid_kwargs("build_patient"))
        raw = p.model_dump()
        view = reasoning_view(raw)
        assert "name" not in view
        assert "address" not in view
        assert "telecom" not in view
        assert "contact" not in view
        assert "birthDate" not in view
        assert isinstance(view.get("ageYears"), int)
        # Only MRN identifier should remain
        assert view["identifier"][0]["value"] == _valid_kwargs("build_patient")["mrn"]

    def test_missing_birth_date_no_crash(self):
        """Patient without birthDate gets no ageYears (no crash)."""
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "name": [{"family": "Smith"}],
        }
        view = reasoning_view(raw)
        assert "birthDate" not in view
        assert "ageYears" not in view

    def test_non_mrn_identifiers_removed(self):
        """Patient with only non-MRN identifiers gets no identifier field."""
        raw = {
            "resourceType": "Patient",
            "id": "p1",
            "birthDate": "2000-01-01",
            "identifier": [
                {
                    "value": "SSN123",
                    "type": {"coding": [{"code": "SS"}]},
                }
            ],
        }
        view = reasoning_view(raw)
        assert "identifier" not in view
