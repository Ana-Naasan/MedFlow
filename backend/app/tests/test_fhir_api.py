"""Tests for FHIR resource model creation, validation, and round-trip fidelity."""

from fhir.resources.R4B.allergyintolerance import AllergyIntolerance
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.medicationstatement import MedicationStatement
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.procedure import Procedure


def _assert_round_trip(model):
    """Assert that a model survives a dict → model → dict round-trip unchanged."""
    dumped = model.model_dump()
    reloaded = model.__class__.model_validate(dumped)
    assert reloaded.model_dump() == dumped


class TestValidation:
    def test_patient(self):
        pat = Patient(
            id="pat-001",
            name=[{"family": "Smith", "given": ["John"]}],
            gender="male",
            birthDate="1990-01-15",
        )
        _assert_round_trip(pat)

    def test_condition(self):
        cond = Condition(
            id="cond-001",
            subject={"reference": "Patient/pat-001"},
            code={
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "38341003",
                        "display": "Hypertension",
                    }
                ]
            },
            clinicalStatus={
                "coding": [
                    {
                        "system": ("http://terminology.hl7.org/CodeSystem" "/condition-clinical"),
                        "code": "active",
                    }
                ]
            },
            verificationStatus={
                "coding": [
                    {
                        "system": ("http://terminology.hl7.org/CodeSystem" "/condition-ver-status"),
                        "code": "confirmed",
                    }
                ]
            },
        )
        _assert_round_trip(cond)

    def test_observation(self):
        obs = Observation(
            id="obs-001",
            status="final",
            code={
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure",
                    }
                ]
            },
            subject={"reference": "Patient/pat-001"},
            valueQuantity={
                "value": 120,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]",
            },
        )
        _assert_round_trip(obs)

    def test_medication_statement(self):
        med_stmt = MedicationStatement(
            id="medstmt-001",
            status="active",
            medicationCodeableConcept={
                "coding": [
                    {
                        "system": ("http://www.nlm.nih.gov/research/umls/rxnorm"),
                        "code": "312961",
                        "display": "Lisinopril 10 MG",
                    }
                ]
            },
            subject={"reference": "Patient/pat-001"},
        )
        _assert_round_trip(med_stmt)

    def test_allergy_intolerance(self):
        allergy = AllergyIntolerance(
            id="allergy-001",
            clinicalStatus={
                "coding": [
                    {
                        "system": (
                            "http://terminology.hl7.org/CodeSystem" "/allergyintolerance-clinical"
                        ),
                        "code": "active",
                    }
                ]
            },
            code={
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "91936005",
                        "display": "Allergy to penicillin",
                    }
                ]
            },
            patient={"reference": "Patient/pat-001"},
        )
        _assert_round_trip(allergy)

    def test_procedure(self):
        proc = Procedure(
            id="proc-001",
            status="completed",
            code={
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "80146002",
                        "display": "Appendectomy",
                    }
                ]
            },
            subject={"reference": "Patient/pat-001"},
            performedDateTime="2024-06-15T10:30:00Z",
        )
        _assert_round_trip(proc)


class TestReference:
    """Reference references like {"reference": "Patient/123"} survive round-trips."""

    def test_reference_dict_preserved(self):
        ref = {"reference": "Patient/123"}
        cond = Condition(
            id="cond-ref-001",
            subject=ref,
            code={
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "73211009",
                        "display": "Diabetes mellitus",
                    }
                ]
            },
            clinicalStatus={
                "coding": [
                    {
                        "system": ("http://terminology.hl7.org/CodeSystem" "/condition-clinical"),
                        "code": "active",
                    }
                ]
            },
            verificationStatus={
                "coding": [
                    {
                        "system": ("http://terminology.hl7.org/CodeSystem" "/condition-ver-status"),
                        "code": "confirmed",
                    }
                ]
            },
        )
        assert cond.model_dump()["subject"] == ref

    def test_reference_round_trip(self):
        ref = {"reference": "Patient/123"}
        cond = Condition(
            id="cond-ref-002",
            subject=ref,
            code={
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "73211009",
                        "display": "Diabetes mellitus",
                    }
                ]
            },
            clinicalStatus={
                "coding": [
                    {
                        "system": ("http://terminology.hl7.org/CodeSystem" "/condition-clinical"),
                        "code": "active",
                    }
                ]
            },
            verificationStatus={
                "coding": [
                    {
                        "system": ("http://terminology.hl7.org/CodeSystem" "/condition-ver-status"),
                        "code": "confirmed",
                    }
                ]
            },
        )
        dumped = cond.model_dump()
        reloaded = Condition.model_validate(dumped)
        assert reloaded.model_dump()["subject"] == ref
