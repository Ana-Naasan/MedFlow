"""Builder functions for a FHIR R4B subset.

Each builder takes plain Python input (dicts, strings, numbers, lists)
and returns a validated fhir.resources R4B model.
"""

from typing import Any

from fhir.resources.R4B.allergyintolerance import AllergyIntolerance
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.medicationstatement import MedicationStatement
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.procedure import Procedure


def _validate(model):
    """Dump and re-validate to ensure a clean round-trip."""
    return model.__class__.model_validate(model.model_dump())


# ── Patient ────────────────────────────────────────────────────────────────


def build_patient(
    *,
    id: str,
    mrn: str,
    family_name: str,
    given_name: str,
    gender: str,
    birth_date: str,
) -> Patient:
    """Build a validated Patient resource keyed on the MRN identifier.

    The raw model retains names, addresses, telecoms, and contacts;
    call :func:`reasoning_view` to obtain a PII-free projection suitable
    for the reasoning engine.
    """
    pat = Patient(
        id=id,
        identifier=[
            {
                "system": "http://hl7.org/fhir/sid/us-mrn",
                "value": mrn,
                "type": {
                    "coding": [
                        {
                            "system": ("http://terminology.hl7.org/CodeSystem"
                                        "/v2-0203"),
                            "code": "MR",
                            "display": "Medical record number",
                        }
                    ]
                },
            }
        ],
        name=[{"family": family_name, "given": [given_name]}],
        gender=gender,
        birthDate=birth_date,
    )
    return _validate(pat)


# ── Condition ──────────────────────────────────────────────────────────────


def build_condition(
    *,
    id: str,
    subject_ref: str,
    code_system: str,
    code: str,
    display: str,
    clinical_status: str = "active",
    verification_status: str = "confirmed",
) -> Condition:
    """Build a validated Condition resource."""
    cond = Condition(
        id=id,
        subject={"reference": subject_ref},
        code={"coding": [{"system": code_system, "code": code, "display": display}]},
        clinicalStatus={
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_status,
                }
            ]
        },
        verificationStatus={
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": verification_status,
                }
            ]
        },
    )
    return _validate(cond)


# ── Observation ────────────────────────────────────────────────────────────


def build_observation(
    *,
    id: str,
    subject_ref: str,
    status: str = "final",
    loinc_code: str,
    loinc_display: str,
    value: float | None = None,
    unit: str = "",
    unit_code: str = "",
) -> Observation:
    """Build a validated Observation resource."""
    obs = Observation(
        id=id,
        status=status,
        code={
            "coding": [
                {"system": "http://loinc.org", "code": loinc_code, "display": loinc_display}
            ]
        },
        subject={"reference": subject_ref},
        valueQuantity=(
            {
                "value": value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": unit_code,
            }
            if value is not None
            else None
        ),
    )
    return _validate(obs)


# ── MedicationStatement ────────────────────────────────────────────────────


def build_medication_statement(
    *,
    id: str,
    subject_ref: str,
    status: str = "active",
    rxnorm_code: str,
    rxnorm_display: str,
) -> MedicationStatement:
    """Build a validated MedicationStatement resource."""
    med = MedicationStatement(
        id=id,
        status=status,
        medicationCodeableConcept={
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": rxnorm_code,
                    "display": rxnorm_display,
                }
            ]
        },
        subject={"reference": subject_ref},
    )
    return _validate(med)


# ── AllergyIntolerance ─────────────────────────────────────────────────────


def build_allergy_intolerance(
    *,
    id: str,
    patient_ref: str,
    code_system: str = "http://snomed.info/sct",
    code: str,
    display: str,
    clinical_status: str = "active",
) -> AllergyIntolerance:
    """Build a validated AllergyIntolerance resource."""
    allergy = AllergyIntolerance(
        id=id,
        clinicalStatus={
            "coding": [
                {
                    "system": (
                        "http://terminology.hl7.org/CodeSystem"
                        "/allergyintolerance-clinical"
                    ),
                    "code": clinical_status,
                }
            ]
        },
        code={"coding": [{"system": code_system, "code": code, "display": display}]},
        patient={"reference": patient_ref},
    )
    return _validate(allergy)


# ── Procedure ──────────────────────────────────────────────────────────────


def build_procedure(
    *,
    id: str,
    subject_ref: str,
    status: str = "completed",
    code_system: str = "http://snomed.info/sct",
    code: str,
    display: str,
    performed_date_time: str | None = None,
) -> Procedure:
    """Build a validated Procedure resource."""
    proc = Procedure(
        id=id,
        status=status,
        code={"coding": [{"system": code_system, "code": code, "display": display}]},
        subject={"reference": subject_ref},
        performedDateTime=performed_date_time,
    )
    return _validate(proc)


# ── Reasoning view (PII-stripped projection) ──────────────────────────────


_PII_KEYS = frozenset({
    "name",
    "address",
    "telecom",
    "contact",
})


def _strip_pii(obj: Any) -> Any:
    """Recursively drop PII keys from a FHIR resource dict."""
    if isinstance(obj, dict):
        return {
            k: _strip_pii(v)
            for k, v in obj.items()
            if k not in _PII_KEYS
        }
    if isinstance(obj, list):
        return [_strip_pii(item) for item in obj]
    return obj


def reasoning_view(resource: dict[str, Any]) -> dict[str, Any]:
    """Return a PII-free projection of a FHIR resource for the reasoning
    engine.

    The following Patient-level fields are **always** stripped:
    ``name``, ``address``, ``telecom``, ``contact``.

    Non-Patient resources are returned with the same top-level fields, but any nested
    Patient fragments (e.g. under ``contained``) also have PII keys stripped.

    Parameters
    ----------
    resource : dict[str, Any]
        A FHIR resource dictionary (e.g. from ``.model_dump()``).

    Returns
    -------
    dict[str, Any]
        A **new** dict with PII keys removed.  The original *resource* is
        not mutated.

    Example
    -------
    >>> raw = {
    ...     "resourceType": "Patient",
    ...     "id": "p1",
    ...     "name": [{"family": "Smith"}],
    ...     "birthDate": "1990-01-15",
    ...     "identifier": [{"value": "MRN001"}],
    ... }
    >>> view = reasoning_view(raw)
    >>> "name" in view
    False
    >>> view["birthDate"]
    '1990-01-15'
    >>> view["identifier"]
    [{'value': 'MRN001'}]
    """
    return _strip_pii(resource)
