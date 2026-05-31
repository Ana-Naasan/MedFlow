"""PostgreSQL connector — reads patient data from hospital databases.

Supports two deliberately different schemas (Institution A and Institution B)
through small per-hospital translation functions that both produce the same
FHIR-like resource dicts.  All connections use READ ONLY transactions so the
database role can never be used to modify hospital data.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
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
            "birthDate": (
                str(patient_row["date_of_birth"]) if patient_row.get("date_of_birth") else None
            ),
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
            "status": lab.get("status", "final"),
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
            entry["valueQuantity"] = {
                "value": float(lab["value"]),
                "unit": lab.get("unit", ""),
                "system": _SYS_UCUM,
                "code": lab.get("unit", ""),
            }
        resources.append(entry)

    for al in related.get("allergies", []):
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
            "birthDate": pt_row.get("dob"),
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
                "status": ev.get("status_flag", "final"),
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
                entry["valueQuantity"] = {
                    "value": float(ev["num_value"]),
                    "unit": ev.get("unit_val", ""),
                    "system": _SYS_UCUM,
                    "code": ev.get("unit_val", ""),
                }
            resources.append(entry)

        elif cls == "ALLERGY":
            resources.append(
                {
                    "resourceType": "AllergyIntolerance",
                    "id": eid,
                    "patient": {"reference": f"Patient/{pid}"},
                    "clinicalStatus": {
                        "coding": [{"system": _SYS_ALLERGY_CLINICAL, "code": "active"}]
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
                "status": "completed",
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
    Every query runs inside a READ ONLY transaction; the database role
    cannot be used to modify any hospital data.
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

    async def _get_pool(self):
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
        seen: set[str] = set()
        coverage: dict[str, dict[str, bool]] = {}
        _cap_map = {
            "Patient": "patient",
            "Condition": "conditions",
            "MedicationStatement": "medications",
            "Observation": "observations",
            "AllergyIntolerance": "allergies",
            "Procedure": "procedures",
        }
        for r in resources:
            cap = _cap_map.get(r.get("resourceType", ""))
            if cap and cap not in seen:
                coverage[cap] = {"requested": True, "returned": True}
                seen.add(cap)
        for cap in _cap_map.values():
            if cap not in coverage:
                coverage[cap] = {"requested": True, "returned": False}

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
