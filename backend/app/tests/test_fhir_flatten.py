"""Tests for fhir/flatten.py — flatten_to_tagged_text()."""

from backend.app.fhir.flatten import flatten_to_tagged_text

_RECORDS = [
    {
        "resourceType": "MedicationStatement",
        "id": "m1",
        "status": "active",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "display": "Lisinopril 10 MG",
                    "code": "312961",
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                }
            ]
        },
        "subject": {"reference": "Patient/p1"},
    },
    {
        "resourceType": "Condition",
        "id": "c1",
        "code": {
            "coding": [
                {
                    "display": "Hypertension",
                    "code": "38341003",
                    "system": "http://snomed.info/sct",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "verificationStatus": {"coding": [{"code": "confirmed"}]},
        "subject": {"reference": "Patient/p1"},
    },
    {
        "resourceType": "Observation",
        "id": "o1",
        "status": "final",
        "code": {
            "coding": [{"display": "Systolic BP", "code": "8480-6", "system": "http://loinc.org"}]
        },
        "valueQuantity": {"value": 120, "unit": "mmHg"},
        "effectiveDateTime": "2024-06-15T00:00:00Z",
        "subject": {"reference": "Patient/p1"},
    },
    # No AllergyIntolerance → should show "not documented"
    {
        "resourceType": "Procedure",
        "id": "p1",
        "status": "completed",
        "code": {
            "coding": [
                {
                    "display": "Appendectomy",
                    "code": "80146002",
                    "system": "http://snomed.info/sct",
                }
            ]
        },
        "performedDateTime": "2024-06-15",
        "subject": {"reference": "Patient/p1"},
    },
]

_NKA_RECORD = [
    {
        "resourceType": "AllergyIntolerance",
        "id": "a1",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "716186003",
                    "display": "No Known Allergy",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "patient": {"reference": "Patient/p1"},
    },
]


# ── Snapshot: [Type/id] tags present ─────────────────────────────────────────


def test_medication_tag_in_output() -> None:
    assert "[MedicationStatement/m1]" in flatten_to_tagged_text(_RECORDS)


def test_condition_tag_in_output() -> None:
    assert "[Condition/c1]" in flatten_to_tagged_text(_RECORDS)


def test_observation_tag_in_output() -> None:
    assert "[Observation/o1]" in flatten_to_tagged_text(_RECORDS)


def test_procedure_tag_in_output() -> None:
    assert "[Procedure/p1]" in flatten_to_tagged_text(_RECORDS)


# ── Values extracted from record, not free text ───────────────────────────────


def test_medication_name_from_record() -> None:
    assert "Lisinopril" in flatten_to_tagged_text(_RECORDS)


def test_observation_value_and_unit_from_record() -> None:
    out = flatten_to_tagged_text(_RECORDS)
    assert "120" in out
    assert "mmHg" in out


def test_procedure_date_from_record() -> None:
    assert "2024-06-15" in flatten_to_tagged_text(_RECORDS)


def test_condition_clinical_status_from_record() -> None:
    assert "active" in flatten_to_tagged_text(_RECORDS)


# ── Missing category still shows ─────────────────────────────────────────────


def test_missing_allergy_category_header_present() -> None:
    out = flatten_to_tagged_text(_RECORDS)
    assert "## Allergies" in out


def test_missing_allergy_shows_not_documented() -> None:
    out = flatten_to_tagged_text(_RECORDS)
    lines = out.splitlines()
    allergy_idx = next(i for i, line in enumerate(lines) if line == "## Allergies")
    assert "not documented" in lines[allergy_idx + 1]


# ── All 5 categories always shown ────────────────────────────────────────────


def test_all_category_headers_present() -> None:
    out = flatten_to_tagged_text(_RECORDS)
    for heading in (
        "## Medications",
        "## Conditions",
        "## Labs & Symptoms",
        "## Allergies",
        "## Procedures",
    ):
        assert heading in out, f"Missing heading: {heading}"


def test_empty_input_shows_all_categories_not_documented() -> None:
    out = flatten_to_tagged_text([])
    for heading in (
        "## Medications",
        "## Conditions",
        "## Labs & Symptoms",
        "## Allergies",
        "## Procedures",
    ):
        assert heading in out
    assert out.count("not documented") == 5


# ── Stated as none (NKA) ─────────────────────────────────────────────────────


def test_nka_shows_stated_as_none() -> None:
    out = flatten_to_tagged_text(_NKA_RECORD)
    assert "[AllergyIntolerance/a1]" in out
    assert "stated as none by source" in out


def test_nka_does_not_show_not_documented() -> None:
    out = flatten_to_tagged_text(_NKA_RECORD)
    allergy_section = out[out.index("## Allergies") :]
    assert "not documented" not in allergy_section.splitlines()[1]


# ── Non-clinical resources silently ignored ───────────────────────────────────


def test_patient_resource_not_rendered() -> None:
    records = [{"resourceType": "Patient", "id": "p1", "name": [{"family": "Smith"}]}]
    out = flatten_to_tagged_text(records)
    assert "[Patient/p1]" not in out


# ── Determinism contract ─────────────────────────────────────────────────────

_TWO_MEDS = [
    {
        "resourceType": "MedicationStatement",
        "id": "m2",
        "status": "active",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "display": "Zeta 5 MG",
                    "code": "2",
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                }
            ]
        },
        "subject": {"reference": "Patient/p1"},
    },
    {
        "resourceType": "MedicationStatement",
        "id": "m1",
        "status": "active",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "display": "Alpha 10 MG",
                    "code": "1",
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                }
            ]
        },
        "subject": {"reference": "Patient/p1"},
    },
]


def test_flatten_is_deterministic() -> None:
    """Same input → byte-identical output across repeated calls."""
    assert flatten_to_tagged_text(_TWO_MEDS) == flatten_to_tagged_text(_TWO_MEDS)


def test_flatten_preserves_input_order_within_category() -> None:
    """Two same-type resources render in input order (m2 before m1), not sorted."""
    out = flatten_to_tagged_text(_TWO_MEDS)
    assert out.index("[MedicationStatement/m2]") < out.index("[MedicationStatement/m1]")
