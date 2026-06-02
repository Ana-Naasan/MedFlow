"""PostgreSQL connector — reads patient data from hospital databases.

Supports two deliberately different schemas (Institution A and Institution B)
through small per-hospital translation functions that both produce the same
FHIR-like resource dicts.  Every query runs inside a ``BEGIN READ ONLY``
transaction, which blocks writes/DDL at the wire level regardless of the
connecting role's grants.  Using a SELECT-only database role (``umraa_reader``
in the seeds) on top of that is defense-in-depth and a deployment concern
(see #67 follow-ups for the docker-compose plumbing).
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, date, datetime
from typing import Any

from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    ConnectorError,
    ConnectorUnavailable,
    FetchResult,
    HealthStatus,
    Provenance,
    Provider,
)

# ── FHIR terminology constants ────────────────────────────────────────────────

_SYS_CONDITION_CLINICAL = "http://terminology.hl7.org/CodeSystem/condition-clinical"
_SYS_ALLERGY_CLINICAL = "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
_SYS_ICD10 = "http://hl7.org/fhir/sid/icd-10"
_SYS_RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
_SYS_LOINC = "http://loinc.org"
_SYS_SNOMED = "http://snomed.info/sct"
_SYS_UCUM = "http://unitsofmeasure.org"

# Valid R4B ObservationStatus value set.
_OBSERVATION_STATUSES = frozenset(
    {
        "registered",
        "preliminary",
        "final",
        "amended",
        "corrected",
        "cancelled",
        "entered-in-error",
        "unknown",
    }
)

# Valid R4B AllergyIntolerance.clinicalStatus value set.
_ALLERGY_CLINICAL_STATUSES = frozenset({"active", "inactive", "resolved"})

# Valid R4B Procedure.status value set.
_PROCEDURE_STATUSES = frozenset(
    {
        "preparation",
        "in-progress",
        "not-done",
        "on-hold",
        "stopped",
        "completed",
        "entered-in-error",
        "unknown",
    }
)


def _iso_date(value: Any) -> str | None:
    """Coerce a date-ish value to ISO ``yyyy-mm-dd`` or ``None``.

    asyncpg returns DATE columns as ``datetime.date`` (Institution A's
    ``patients.date_of_birth``); Institution B stores DOB in a ``VARCHAR``
    that comes back as ``str``. Both must serialise identically so the
    downstream FHIR ``birthDate`` value compares equal across schemas
    (#67 honesty/fidelity).

    Empty strings and ``None`` collapse to ``None`` so missing DOBs are
    consistently absent rather than stringified ``"None"``.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip() or None
    return str(value).strip() or None


def _allergy_clinical_status(raw: str | None) -> str:
    """Coerce a source flag onto the R4B AllergyIntolerance.clinicalStatus
    value set (active / inactive / resolved).

    Institution B's per-event ``status_flag`` may carry tokens like
    ``active``/``resolved``/``inactive`` directly. Unknown tokens fall back
    to ``active`` — the safer-than-silently-dropping default already used
    when no status column exists (Institution A).
    """
    if raw is None:
        return "active"
    norm = str(raw).strip().lower()
    return norm if norm in _ALLERGY_CLINICAL_STATUSES else "active"


def _procedure_status(raw: str | None) -> str:
    """Coerce a source flag onto the R4B Procedure.status value set.

    Institution B reuses one ``status_flag`` column across event classes,
    so a PROC row may carry tokens like ``completed``, ``in-progress``,
    ``active`` (from RX vocabulary), or ``done``. Map common synonyms and
    fall back to ``unknown`` rather than overstating ``completed`` for
    a token we don't recognise.
    """
    if raw is None:
        return "completed"
    norm = str(raw).strip().lower()
    if norm in _PROCEDURE_STATUSES:
        return norm
    # Common cross-vocabulary synonyms:
    if norm in {"active", "ongoing"}:
        return "in-progress"
    if norm in {"done", "finished"}:
        return "completed"
    if norm in {"cancelled", "canceled", "aborted"}:
        return "stopped"
    return "unknown"


def _observation_status(raw: str | None) -> str:
    """Coerce a source status into a valid R4B ObservationStatus.

    Institution B overloads a single ``status_flag`` column across event classes
    (RX uses ``active``/``stopped`` etc.), so a LAB row could carry a token that
    is not an ObservationStatus — fhir.resources does not enforce the value set,
    so map it explicitly here, defaulting unknown tokens to ``final``.
    """
    status = (raw or "final").strip().lower()
    return status if status in _OBSERVATION_STATUSES else "final"


def _value_quantity(value: float, unit: str | None) -> dict:
    """Build a valid R4B ``valueQuantity``.

    UCUM ``system``/``code`` are attached ONLY when a unit is present: a populated
    ``system`` alongside an empty ``code`` (the missing-unit case) fails R4B
    Quantity validation (``code`` is a non-empty primitive).
    """
    quantity: dict = {"value": float(value)}
    if unit:
        quantity["unit"] = unit
        quantity["system"] = _SYS_UCUM
        quantity["code"] = unit
    return quantity


# ── Institution A translation (EMR-style, separate tables) ────────────────────


def _translate_a(
    patient_row: dict[str, Any],
    related: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict], list[str]]:
    """Map Institution A's rows to FHIR-like resource dicts."""
    resources: list[dict] = []
    warnings: list[str] = []
    pid = patient_row["patient_id"]

    resources.append(
        {
            "resourceType": "Patient",
            "id": pid,
            "gender": {"m": "male", "f": "female"}.get(
                str(patient_row.get("sex", "")).lower(), "unknown"
            ),
            "birthDate": _iso_date(patient_row.get("date_of_birth")),
        }
    )

    for dx in related.get("diagnoses", []):
        resources.append(
            {
                "resourceType": "Condition",
                "id": dx["diagnosis_id"],
                "subject": {"reference": f"Patient/{pid}"},
                "code": {
                    "coding": [
                        {
                            "system": _SYS_ICD10,
                            "code": dx["icd10_code"],
                            "display": dx.get("description", ""),
                        }
                    ]
                },
                "clinicalStatus": {
                    "coding": [
                        {"system": _SYS_CONDITION_CLINICAL, "code": dx.get("status", "active")}
                    ]
                },
            }
        )

    for rx in related.get("prescriptions", []):
        resources.append(
            {
                "resourceType": "MedicationStatement",
                "id": rx["prescription_id"],
                "status": "active" if rx.get("active") else "stopped",
                "subject": {"reference": f"Patient/{pid}"},
                "medicationCodeableConcept": {
                    "coding": [
                        {
                            "system": _SYS_RXNORM,
                            "code": rx["rxnorm_code"],
                            "display": rx.get("drug_name", ""),
                        }
                    ]
                },
            }
        )

    for lab in related.get("lab_results", []):
        entry: dict = {
            "resourceType": "Observation",
            "id": lab["result_id"],
            "status": _observation_status(lab.get("status")),
            "subject": {"reference": f"Patient/{pid}"},
            "code": {
                "coding": [
                    {
                        "system": _SYS_LOINC,
                        "code": lab["loinc_code"],
                        "display": lab.get("description", ""),
                    }
                ]
            },
        }
        if lab.get("value") is not None:
            entry["valueQuantity"] = _value_quantity(lab["value"], lab.get("unit"))
        resources.append(entry)

    for al in related.get("allergies", []):
        # Institution A's ``allergies`` table has no status column — every row
        # is assumed active (per the hospital's data dictionary). When the
        # schema is later extended, route the column through
        # ``_allergy_clinical_status`` like Institution B does.
        resources.append(
            {
                "resourceType": "AllergyIntolerance",
                "id": al["allergy_id"],
                "patient": {"reference": f"Patient/{pid}"},
                "clinicalStatus": {"coding": [{"system": _SYS_ALLERGY_CLINICAL, "code": "active"}]},
                "code": {
                    "coding": [
                        {
                            "system": _SYS_SNOMED,
                            "code": al["snomed_code"],
                            "display": al.get("substance", ""),
                        }
                    ]
                },
            }
        )

    for proc in related.get("procedures", []):
        # Institution A's ``procedures_done`` table records only completed
        # procedures (per the hospital's data dictionary), so ``status`` is
        # hard-coded ``completed``. If A ever surfaces an in-progress or
        # cancelled procedure column, route it through ``_procedure_status``
        # like Institution B does.
        entry = {
            "resourceType": "Procedure",
            "id": proc["procedure_id"],
            "status": "completed",
            "subject": {"reference": f"Patient/{pid}"},
            "code": {
                "coding": [
                    {
                        "system": _SYS_SNOMED,
                        "code": proc["snomed_code"],
                        "display": proc.get("description", ""),
                    }
                ]
            },
        }
        if proc.get("performed_on"):
            entry["performedDateTime"] = str(proc["performed_on"])
        resources.append(entry)

    return resources, warnings


# ── Institution B translation (flat legacy schema, all events in one table) ──


def _translate_b(
    pt_row: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[list[dict], list[str]]:
    """Map Institution B's rows to FHIR-like resource dicts."""
    resources: list[dict] = []
    warnings: list[str] = []
    pid = str(pt_row["pt_ref"]).strip()

    resources.append(
        {
            "resourceType": "Patient",
            "id": pid,
            "gender": {"M": "male", "F": "female"}.get(
                str(pt_row.get("gender_code", "")).strip(), "unknown"
            ),
            "birthDate": _iso_date(pt_row.get("dob")),
        }
    )

    for ev in events:
        eid = str(ev["event_id"])
        cls = ev.get("event_class", "")

        if cls == "DX":
            resources.append(
                {
                    "resourceType": "Condition",
                    "id": eid,
                    "subject": {"reference": f"Patient/{pid}"},
                    "code": {
                        "coding": [
                            {
                                "system": _SYS_ICD10,
                                "code": ev["code"],
                                "display": ev.get("description", ""),
                            }
                        ]
                    },
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": _SYS_CONDITION_CLINICAL,
                                "code": ev.get("status_flag", "active"),
                            }
                        ]
                    },
                }
            )

        elif cls == "RX":
            resources.append(
                {
                    "resourceType": "MedicationStatement",
                    "id": eid,
                    "status": "active" if ev.get("status_flag") == "active" else "stopped",
                    "subject": {"reference": f"Patient/{pid}"},
                    "medicationCodeableConcept": {
                        "coding": [
                            {
                                "system": _SYS_RXNORM,
                                "code": ev["code"],
                                "display": ev.get("description", ""),
                            }
                        ]
                    },
                }
            )

        elif cls == "LAB":
            entry: dict = {
                "resourceType": "Observation",
                "id": eid,
                "status": _observation_status(ev.get("status_flag")),
                "subject": {"reference": f"Patient/{pid}"},
                "code": {
                    "coding": [
                        {
                            "system": _SYS_LOINC,
                            "code": ev["code"],
                            "display": ev.get("description", ""),
                        }
                    ]
                },
            }
            if ev.get("num_value") is not None:
                entry["valueQuantity"] = _value_quantity(ev["num_value"], ev.get("unit_val"))
            resources.append(entry)

        elif cls == "ALLERGY":
            resources.append(
                {
                    "resourceType": "AllergyIntolerance",
                    "id": eid,
                    "patient": {"reference": f"Patient/{pid}"},
                    "clinicalStatus": {
                        "coding": [
                            {
                                "system": _SYS_ALLERGY_CLINICAL,
                                "code": _allergy_clinical_status(ev.get("status_flag")),
                            }
                        ]
                    },
                    "code": {
                        "coding": [
                            {
                                "system": _SYS_SNOMED,
                                "code": ev["code"],
                                "display": ev.get("description", ""),
                            }
                        ]
                    },
                }
            )

        elif cls == "PROC":
            entry = {
                "resourceType": "Procedure",
                "id": eid,
                "status": _procedure_status(ev.get("status_flag")),
                "subject": {"reference": f"Patient/{pid}"},
                "code": {
                    "coding": [
                        {
                            "system": _SYS_SNOMED,
                            "code": ev["code"],
                            "display": ev.get("description", ""),
                        }
                    ]
                },
            }
            if ev.get("event_date"):
                entry["performedDateTime"] = str(ev["event_date"])
            resources.append(entry)

        else:
            warnings.append(f"Unknown event_class {cls!r} for event_id={eid}")

    return resources, warnings


# ── asyncpg fetch helpers ─────────────────────────────────────────────────────


async def _fetch_raw_a(conn, patient_id: str) -> tuple[dict, dict[str, list[dict]]]:
    """Fetch from Institution A's normalised schema."""
    patient = await conn.fetchrow(
        "SELECT patient_id, date_of_birth, sex FROM patients WHERE patient_id = $1",
        patient_id,
    )
    if patient is None:
        raise ConnectorDataError(f"Patient {patient_id!r} not found in institution A")

    diagnoses = await conn.fetch(
        "SELECT diagnosis_id, patient_id, icd10_code, description, status"
        " FROM diagnoses WHERE patient_id = $1",
        patient_id,
    )
    prescriptions = await conn.fetch(
        "SELECT prescription_id, patient_id, drug_name, rxnorm_code, active"
        " FROM prescriptions WHERE patient_id = $1",
        patient_id,
    )
    lab_results = await conn.fetch(
        "SELECT result_id, patient_id, loinc_code, description, value, unit, status"
        " FROM lab_results WHERE patient_id = $1",
        patient_id,
    )
    allergies = await conn.fetch(
        "SELECT allergy_id, patient_id, substance, snomed_code"
        " FROM drug_allergies WHERE patient_id = $1",
        patient_id,
    )
    procedures = await conn.fetch(
        "SELECT procedure_id, patient_id, snomed_code, description, performed_on"
        " FROM procedures_done WHERE patient_id = $1",
        patient_id,
    )

    return dict(patient), {
        "diagnoses": [dict(r) for r in diagnoses],
        "prescriptions": [dict(r) for r in prescriptions],
        "lab_results": [dict(r) for r in lab_results],
        "allergies": [dict(r) for r in allergies],
        "procedures": [dict(r) for r in procedures],
    }


async def _fetch_raw_b(conn, patient_id: str) -> tuple[dict, list[dict]]:
    """Fetch from Institution B's flat event schema."""
    pt = await conn.fetchrow(
        "SELECT pt_ref, dob, gender_code FROM pt_registry WHERE TRIM(pt_ref) = $1",
        patient_id,
    )
    if pt is None:
        raise ConnectorDataError(f"Patient {patient_id!r} not found in institution B")

    events = await conn.fetch(
        "SELECT event_id, pt_ref, event_class, code, code_system,"
        " description, num_value, unit_val, status_flag, event_date"
        " FROM clinical_events WHERE TRIM(pt_ref) = $1 ORDER BY event_id",
        patient_id,
    )
    return dict(pt), [dict(e) for e in events]


# ── Provider ──────────────────────────────────────────────────────────────────


class PostgresProvider(Provider):
    """Read-only connector for hospital PostgreSQL databases.

    Supports two institution schemas (``institution="a"`` or ``"b"``).

    Read-only guarantee
    -------------------
    Every query runs inside a Postgres ``BEGIN READ ONLY`` transaction,
    which blocks ``INSERT`` / ``UPDATE`` / ``DELETE`` / DDL at the wire
    level regardless of the connecting role's grants. This is the
    invariant the connector enforces and is what the tests pin.

    The shipped seeds also define a ``umraa_reader`` role with
    ``GRANT SELECT`` as defense-in-depth, but **wiring the connector to
    that role is deployment guidance** — the runtime credential is
    whatever the operator passes via ``dsn``. See #67 follow-ups for the
    docker-compose plumbing.
    """

    id = "postgres"
    capabilities = (
        Capability.PATIENT
        | Capability.MEDICATIONS
        | Capability.CONDITIONS
        | Capability.ALLERGIES
        | Capability.OBSERVATIONS
        | Capability.PROCEDURES
    )

    def __init__(
        self,
        *,
        dsn: str,
        institution: str,
        pool=None,
    ) -> None:
        self._dsn = dsn
        self._institution = institution.lower()
        self._pool = pool  # injectable for tests; created lazily in production
        # Guards the lazy pool creation: without this, two concurrent
        # ``fetch_patient`` calls on a cold provider race past the ``is None``
        # check and both ``asyncpg.create_pool``, leaking the loser's pool.
        self._pool_lock = asyncio.Lock()

    async def _get_pool(self):
        # Double-checked: the fast path stays lock-free once the pool exists.
        if self._pool is not None:
            return self._pool
        async with self._pool_lock:
            if self._pool is not None:
                return self._pool
            import asyncpg

            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=3)
            return self._pool

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                async with conn.transaction(readonly=True):
                    if self._institution == "a":
                        patient_row, related = await _fetch_raw_a(conn, patient_id)
                        resources, warnings = _translate_a(patient_row, related)
                    elif self._institution == "b":
                        pt_row, events = await _fetch_raw_b(conn, patient_id)
                        resources, warnings = _translate_b(pt_row, events)
                    else:
                        raise ConnectorDataError(
                            f"Unknown institution {self._institution!r}; expected 'a' or 'b'"
                        )
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorUnavailable(
                f"Postgres unreachable ({self._institution}): {exc}"
            ) from exc

        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [{"resource": r} for r in resources],
        }
        provenance = [
            Provenance(
                resource_ref=f"{r['resourceType']}/{r['id']}",
                source_provider=self.id,
                source_record_id=r["id"],
            )
            for r in resources
            if r.get("id")
        ]
        # Coverage is driven by ``self.capabilities``: ``requested`` is True
        # only for capabilities the connector actually advertises (#67 honesty
        # bullet). Capabilities the connector does NOT support are absent from
        # the coverage dict — they're not "missing", they're "out of scope".
        _cap_flag_for_type: dict[str, tuple[str, Capability]] = {
            "Patient": ("patient", Capability.PATIENT),
            "Condition": ("conditions", Capability.CONDITIONS),
            "MedicationStatement": ("medications", Capability.MEDICATIONS),
            "Observation": ("observations", Capability.OBSERVATIONS),
            "AllergyIntolerance": ("allergies", Capability.ALLERGIES),
            "Procedure": ("procedures", Capability.PROCEDURES),
        }
        returned_caps: set[str] = {
            _cap_flag_for_type[rtype][0]
            for r in resources
            if (rtype := r.get("resourceType", "")) in _cap_flag_for_type
        }

        coverage: dict[str, dict[str, bool]] = {}
        for cap_name, cap_flag in _cap_flag_for_type.values():
            if self.supports(cap_flag):
                coverage[cap_name] = {
                    "requested": True,
                    "returned": cap_name in returned_caps,
                }

        # Partial honesty: when a supported capability returns no records we
        # can't know whether the patient truly has none or the fetch was
        # incomplete (absence ≠ none, #30/#67). Append a soft note and let
        # ``partial`` reflect that — this is what flips ``partial_data_notice``
        # into a non-empty surface in the /packet response.
        empty_caps = sorted(
            name for name, flags in coverage.items() if flags["requested"] and not flags["returned"]
        )
        if empty_caps:
            label = "category" if len(empty_caps) == 1 else "categories"
            warnings.append(f"No records returned for supported {label}: " + ", ".join(empty_caps))

        return FetchResult(
            bundle=bundle,
            source=self.id,
            fetched_at=datetime.now(UTC),
            partial=bool(warnings),
            warnings=warnings,
            provenance=provenance,
            coverage=coverage,
        )

    async def health_check(self) -> HealthStatus:
        t0 = time.monotonic()
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return HealthStatus(ok=True, latency_ms=(time.monotonic() - t0) * 1000)
        except Exception as exc:
            return HealthStatus(ok=False, latency_ms=0.0, detail=str(exc))

    async def aclose(self) -> None:
        """Close the connection pool if one was created (e.g. by a health probe).

        Uses terminate() rather than the graceful close() so it can never block on
        a connection a cancelled probe left checked out.
        """
        pool = self._pool
        if pool is not None:
            self._pool = None
            pool.terminate()
