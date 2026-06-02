"""FHIR R4B boundary validation (FHIR-01/02).

The ``/intake`` boundary is the trust seam: a connector hands us FHIR-shaped dicts
and we must not let malformed resources into the cache / reasoning / citation path.
:func:`validate_fhir_resource` re-validates each fetched resource against the
6-resource R4B subset and reports a **SEC-02-sanitised** warning on failure — the
raw pydantic ``ValidationError`` is never surfaced, because its ``input_value``
echoes Patient name/address/telecom.

**Skip-with-gap, not raise-on-failure (intentional refinement of FHIR-01).**
The spec phrases boundary validation as ``model_validate() ... (raise on failure)``.
We deliberately refine that: an in-subset resource that fails validation is *dropped
and surfaced as an honest data gap* rather than 4xx-ing the whole intake. A single
malformed resource must never zero a partial fetch (CONN-06; "absence =
unknown, never none"). Out-of-subset types are an expected projection boundary —
Umraa reasons over only these 6 types — so they are filtered silently, not flagged.
"""

from __future__ import annotations

# The R4B subset Umraa reasons over. Lazy-loaded so importing this module does not
# require ``fhir.resources`` at import time (mirrors providers.mock_fhir).
_VALIDATORS: dict[str, type] = {}


def _load_validators() -> dict[str, type]:
    global _VALIDATORS
    if _VALIDATORS:
        return _VALIDATORS
    from fhir.resources.R4B.allergyintolerance import AllergyIntolerance
    from fhir.resources.R4B.condition import Condition
    from fhir.resources.R4B.medicationstatement import MedicationStatement
    from fhir.resources.R4B.observation import Observation
    from fhir.resources.R4B.patient import Patient
    from fhir.resources.R4B.procedure import Procedure

    _VALIDATORS = {
        "Patient": Patient,
        "Condition": Condition,
        "MedicationStatement": MedicationStatement,
        "Observation": Observation,
        "AllergyIntolerance": AllergyIntolerance,
        "Procedure": Procedure,
    }
    return _VALIDATORS


def validate_fhir_resource(
    resource: object, *, _validators: dict[str, type] | None = None
) -> tuple[bool, str | None]:
    """Validate one fetched resource against the R4B subset.

    Returns ``(True, None)`` when the resource conforms to one of the 6 subset
    types. Returns ``(False, warning)`` when it is in-subset but fails validation —
    the warning names only the resource type/id and the exception **class** name,
    never the raw ``ValidationError`` (SEC-02). Returns ``(False, None)`` for a
    resource outside the subset: an expected filter, not an error, so no warning.

    *_validators* is injectable so tests run without ``fhir.resources``.
    """
    if not isinstance(resource, dict):
        return False, "Skipped a resource that is not a FHIR object"
    validators = _validators if _validators is not None else _load_validators()
    rtype = resource.get("resourceType")
    if rtype not in validators:
        return False, None  # outside the 6-type subset — silently filtered, not an error
    rid = resource.get("id", "?")
    try:
        validators[rtype].model_validate(resource)
    except Exception as exc:  # noqa: BLE001 — any validation failure is a skip, never a 500
        return False, f"Skipped {rtype}/{rid}: validation failed ({type(exc).__name__})"
    return True, None
