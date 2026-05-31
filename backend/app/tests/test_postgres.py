"""Tests for the PostgreSQL connector.

All tests use lightweight mock pools/connections — no running Postgres required.
The translation functions (_translate_a, _translate_b) are pure and tested
directly; the provider tests verify connection lifecycle and error handling.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.providers.base import ConnectorDataError, ConnectorUnavailable
from backend.app.providers.postgres import (
    PostgresProvider,
    _fetch_raw_a,
    _fetch_raw_b,
    _observation_status,
    _translate_a,
    _translate_b,
    _value_quantity,
)

# ── shared test data ──────────────────────────────────────────────────────────

_PATIENT_ID = "DEMO-001"

# Institution A rows (normalised, separate tables)
_IA_PATIENT = {"patient_id": _PATIENT_ID, "date_of_birth": "1950-03-15", "sex": "M"}
_IA_RELATED: dict[str, list[dict]] = {
    "diagnoses": [
        {
            "diagnosis_id": "D001",
            "patient_id": _PATIENT_ID,
            "icd10_code": "E11",
            "description": "Type 2 diabetes mellitus",
            "status": "active",
        },
    ],
    "prescriptions": [
        {
            "prescription_id": "R001",
            "patient_id": _PATIENT_ID,
            "drug_name": "Metformin 500 MG Oral Tablet",
            "rxnorm_code": "860975",
            "active": True,
        },
    ],
    "lab_results": [
        {
            "result_id": "L001",
            "patient_id": _PATIENT_ID,
            "loinc_code": "4548-4",
            "description": "HbA1c",
            "value": 7.4,
            "unit": "%",
            "status": "final",
        },
    ],
    "allergies": [
        {
            "allergy_id": "A001",
            "patient_id": _PATIENT_ID,
            "substance": "Amoxicillin",
            "snomed_code": "372687004",
        },
    ],
    "procedures": [
        {
            "procedure_id": "P001",
            "patient_id": _PATIENT_ID,
            "snomed_code": "36228007",
            "description": "Eye exam",
            "performed_on": "2023-06-15",
        },
    ],
}

# Institution B rows (flat event table, same clinical profile)
_IB_PATIENT = {"pt_ref": "DEMO-001    ", "dob": "1950-03-15", "gender_code": "M"}
_IB_EVENTS: list[dict[str, Any]] = [
    {
        "event_id": 1,
        "pt_ref": "DEMO-001    ",
        "event_class": "DX",
        "code": "E11",
        "code_system": "ICD10",
        "description": "Type 2 diabetes mellitus",
        "num_value": None,
        "unit_val": None,
        "status_flag": "active",
        "event_date": None,
    },
    {
        "event_id": 2,
        "pt_ref": "DEMO-001    ",
        "event_class": "RX",
        "code": "860975",
        "code_system": "RXNORM",
        "description": "Metformin 500 MG Oral Tablet",
        "num_value": None,
        "unit_val": None,
        "status_flag": "active",
        "event_date": None,
    },
    {
        "event_id": 3,
        "pt_ref": "DEMO-001    ",
        "event_class": "LAB",
        "code": "4548-4",
        "code_system": "LOINC",
        "description": "HbA1c",
        "num_value": 7.4,
        "unit_val": "%",
        "status_flag": "final",
        "event_date": None,
    },
    {
        "event_id": 4,
        "pt_ref": "DEMO-001    ",
        "event_class": "ALLERGY",
        "code": "372687004",
        "code_system": "SNOMED",
        "description": "Amoxicillin",
        "num_value": None,
        "unit_val": None,
        "status_flag": "active",
        "event_date": None,
    },
    {
        "event_id": 5,
        "pt_ref": "DEMO-001    ",
        "event_class": "PROC",
        "code": "36228007",
        "code_system": "SNOMED",
        "description": "Eye exam",
        "num_value": None,
        "unit_val": None,
        "status_flag": "completed",
        "event_date": "2023-06-15",
    },
]


# ── helpers ───────────────────────────────────────────────────────────────────


def _by_type(resources: list[dict], rtype: str) -> list[dict]:
    return [r for r in resources if r.get("resourceType") == rtype]


def _one(resources: list[dict], rtype: str) -> dict:
    hits = _by_type(resources, rtype)
    assert hits, f"No {rtype} in resources"
    return hits[0]


# ── Institution A → records ───────────────────────────────────────────────────


def test_institution_a_patient_fields():
    resources, warnings = _translate_a(_IA_PATIENT, _IA_RELATED)
    patient = _one(resources, "Patient")
    assert patient["id"] == _PATIENT_ID
    assert patient["gender"] == "male"
    assert patient["birthDate"] == "1950-03-15"
    assert warnings == []


def test_institution_a_condition():
    resources, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    cond = _one(resources, "Condition")
    assert cond["code"]["coding"][0]["code"] == "E11"
    assert cond["subject"]["reference"] == f"Patient/{_PATIENT_ID}"
    assert cond["clinicalStatus"]["coding"][0]["code"] == "active"


def test_institution_a_medication():
    resources, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    med = _one(resources, "MedicationStatement")
    assert med["medicationCodeableConcept"]["coding"][0]["code"] == "860975"
    assert med["status"] == "active"


def test_institution_a_observation_with_value():
    resources, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    obs = _one(resources, "Observation")
    assert obs["code"]["coding"][0]["code"] == "4548-4"
    assert obs["valueQuantity"]["value"] == pytest.approx(7.4)
    assert obs["valueQuantity"]["unit"] == "%"


def test_institution_a_observation_no_value():
    related = {
        **_IA_RELATED,
        "lab_results": [
            {
                "result_id": "L99",
                "patient_id": _PATIENT_ID,
                "loinc_code": "4548-4",
                "description": "HbA1c",
                "value": None,
                "unit": "",
                "status": "final",
            },
        ],
    }
    resources, _ = _translate_a(_IA_PATIENT, related)
    obs = _one(resources, "Observation")
    assert "valueQuantity" not in obs


def test_institution_a_allergy():
    resources, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    al = _one(resources, "AllergyIntolerance")
    assert al["code"]["coding"][0]["code"] == "372687004"
    assert al["patient"]["reference"] == f"Patient/{_PATIENT_ID}"


def test_institution_a_procedure_with_date():
    resources, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    proc = _one(resources, "Procedure")
    assert proc["code"]["coding"][0]["code"] == "36228007"
    assert proc["performedDateTime"] == "2023-06-15"


def test_institution_a_procedure_no_date():
    related = {
        **_IA_RELATED,
        "procedures": [
            {
                "procedure_id": "P99",
                "patient_id": _PATIENT_ID,
                "snomed_code": "36228007",
                "description": "Eye exam",
                "performed_on": None,
            },
        ],
    }
    resources, _ = _translate_a(_IA_PATIENT, related)
    proc = _one(resources, "Procedure")
    assert "performedDateTime" not in proc


def test_institution_a_inactive_medication():
    related = {
        **_IA_RELATED,
        "prescriptions": [
            {
                "prescription_id": "R99",
                "patient_id": _PATIENT_ID,
                "drug_name": "Aspirin",
                "rxnorm_code": "1191",
                "active": False,
            },
        ],
    }
    resources, _ = _translate_a(_IA_PATIENT, related)
    med = _one(resources, "MedicationStatement")
    assert med["status"] == "stopped"


def test_institution_a_unknown_sex():
    patient = {**_IA_PATIENT, "sex": "X"}
    resources, _ = _translate_a(patient, {})
    assert _one(resources, "Patient")["gender"] == "unknown"


# ── Institution B → records (same clinical profile, proved identical) ─────────


def test_institution_b_patient_fields():
    resources, warnings = _translate_b(_IB_PATIENT, _IB_EVENTS)
    patient = _one(resources, "Patient")
    assert patient["id"] == _PATIENT_ID  # TRIM applied
    assert patient["gender"] == "male"  # same as institution A
    assert patient["birthDate"] == "1950-03-15"  # same as institution A
    assert warnings == []


def test_institution_b_condition_matches_a():
    resources_a, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    resources_b, _ = _translate_b(_IB_PATIENT, _IB_EVENTS)

    code_a = _one(resources_a, "Condition")["code"]["coding"][0]["code"]
    code_b = _one(resources_b, "Condition")["code"]["coding"][0]["code"]
    assert code_a == code_b == "E11"


def test_institution_b_medication_matches_a():
    resources_a, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    resources_b, _ = _translate_b(_IB_PATIENT, _IB_EVENTS)

    code_a = _one(resources_a, "MedicationStatement")["medicationCodeableConcept"]["coding"][0][
        "code"
    ]
    code_b = _one(resources_b, "MedicationStatement")["medicationCodeableConcept"]["coding"][0][
        "code"
    ]
    assert code_a == code_b == "860975"


def test_institution_b_observation_with_value():
    resources, _ = _translate_b(_IB_PATIENT, _IB_EVENTS)
    obs = _one(resources, "Observation")
    assert obs["code"]["coding"][0]["code"] == "4548-4"
    assert obs["valueQuantity"]["value"] == pytest.approx(7.4)


def test_institution_b_observation_no_value():
    events = [
        {
            "event_id": 99,
            "pt_ref": "DEMO-001    ",
            "event_class": "LAB",
            "code": "4548-4",
            "code_system": "LOINC",
            "description": "HbA1c",
            "num_value": None,
            "unit_val": None,
            "status_flag": "final",
            "event_date": None,
        }
    ]
    resources, _ = _translate_b(_IB_PATIENT, events)
    obs = _one(resources, "Observation")
    assert "valueQuantity" not in obs


def test_institution_b_allergy():
    resources, _ = _translate_b(_IB_PATIENT, _IB_EVENTS)
    al = _one(resources, "AllergyIntolerance")
    assert al["code"]["coding"][0]["code"] == "372687004"


def test_institution_b_procedure_with_date():
    resources, _ = _translate_b(_IB_PATIENT, _IB_EVENTS)
    proc = _one(resources, "Procedure")
    assert proc["code"]["coding"][0]["code"] == "36228007"
    assert proc["performedDateTime"] == "2023-06-15"


def test_institution_b_procedure_no_date():
    events = [
        {
            "event_id": 99,
            "pt_ref": "DEMO-001    ",
            "event_class": "PROC",
            "code": "36228007",
            "code_system": "SNOMED",
            "description": "Eye exam",
            "num_value": None,
            "unit_val": None,
            "status_flag": "completed",
            "event_date": None,
        }
    ]
    resources, _ = _translate_b(_IB_PATIENT, events)
    proc = _one(resources, "Procedure")
    assert "performedDateTime" not in proc


def test_institution_b_inactive_medication():
    events = [
        {
            "event_id": 9,
            "pt_ref": "DEMO-001    ",
            "event_class": "RX",
            "code": "1191",
            "code_system": "RXNORM",
            "description": "Aspirin",
            "num_value": None,
            "unit_val": None,
            "status_flag": "stopped",
            "event_date": None,
        }
    ]
    resources, _ = _translate_b(_IB_PATIENT, events)
    assert _one(resources, "MedicationStatement")["status"] == "stopped"


def test_institution_b_unknown_event_class_emits_warning():
    events = [
        {
            "event_id": 9,
            "pt_ref": "DEMO-001    ",
            "event_class": "UNKNOWN",
            "code": "X",
            "code_system": "?",
            "description": "",
            "num_value": None,
            "unit_val": None,
            "status_flag": None,
            "event_date": None,
        }
    ]
    resources, warnings = _translate_b(_IB_PATIENT, events)
    assert not _by_type(resources, "Observation")
    assert any("UNKNOWN" in w for w in warnings)


def test_institution_b_unknown_gender():
    pt = {**_IB_PATIENT, "gender_code": "U"}
    resources, _ = _translate_b(pt, [])
    assert _one(resources, "Patient")["gender"] == "unknown"


# ── Write-is-rejected test ────────────────────────────────────────────────────


def test_fetch_patient_opens_readonly_transaction():
    """Provider must open a READ ONLY transaction; the DB rejects any DML inside it."""
    readonly_flags: list[bool] = []

    class _Txn:
        def __init__(self, **kwargs: Any) -> None:
            readonly_flags.append(kwargs.get("readonly", False))

        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **kwargs: Any) -> _Txn:
            return _Txn(**kwargs)

        async def fetchrow(self, *_: Any) -> None:
            return None  # patient not found → ConnectorDataError

        async def fetch(self, *_: Any) -> list:
            return []

    class _Acquire:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Pool:
        def acquire(self) -> _Acquire:
            return _Acquire()

    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=_Pool())

    with pytest.raises(ConnectorDataError):
        asyncio.run(provider.fetch_patient(_PATIENT_ID))

    assert readonly_flags == [True], "transaction must be opened with readonly=True"


# ── Provider error paths ──────────────────────────────────────────────────────


def test_fetch_patient_unknown_institution():
    class _Pool:
        def acquire(self) -> _Acquire:
            return _Acquire()

    class _Acquire:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **kwargs: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, *_: Any) -> None:
            return None

        async def fetch(self, *_: Any) -> list:
            return []

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    provider = PostgresProvider(dsn="postgresql://x", institution="z", pool=_Pool())
    with pytest.raises(ConnectorDataError, match="Unknown institution"):
        asyncio.run(provider.fetch_patient(_PATIENT_ID))


def test_fetch_patient_wraps_unexpected_exception():
    class _BrokenPool:
        def acquire(self) -> MagicMock:
            raise RuntimeError("no connection")

    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=_BrokenPool())
    with pytest.raises(ConnectorUnavailable, match="Postgres unreachable"):
        asyncio.run(provider.fetch_patient(_PATIENT_ID))


def test_fetch_patient_institution_a_full_result():
    """fetch_patient returns a valid FetchResult with all 6 coverage keys for institution A."""

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **_: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, sql: str, *args: Any):
            return {"patient_id": _PATIENT_ID, "date_of_birth": "1950-03-15", "sex": "F"}

        async def fetch(self, sql: str, *args: Any) -> list:
            return []

    class _Acquire:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Pool:
        def acquire(self) -> _Acquire:
            return _Acquire()

    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=_Pool())
    result = asyncio.run(provider.fetch_patient(_PATIENT_ID))

    assert result.source == "postgres"
    assert result.bundle["resourceType"] == "Bundle"
    assert result.coverage["patient"]["returned"] is True
    assert set(result.coverage.keys()) == {
        "patient",
        "conditions",
        "medications",
        "observations",
        "allergies",
        "procedures",
    }


def test_fetch_patient_institution_b_full_result():
    """fetch_patient returns a valid FetchResult for institution B."""

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **_: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, sql: str, *args: Any):
            return {"pt_ref": "DEMO-001    ", "dob": "1950-03-15", "gender_code": "M"}

        async def fetch(self, sql: str, *args: Any) -> list:
            return []

    class _Acquire:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Pool:
        def acquire(self) -> _Acquire:
            return _Acquire()

    provider = PostgresProvider(dsn="postgresql://x", institution="b", pool=_Pool())
    result = asyncio.run(provider.fetch_patient(_PATIENT_ID))

    assert result.source == "postgres"
    assert result.coverage["patient"]["returned"] is True


# ── health_check ──────────────────────────────────────────────────────────────


def test_health_check_ok():
    class _Conn:
        async def fetchval(self, *_: Any) -> int:
            return 1

    class _Acquire:
        async def __aenter__(self) -> _Conn:
            return _Conn()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Pool:
        def acquire(self) -> _Acquire:
            return _Acquire()

    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=_Pool())
    status = asyncio.run(provider.health_check())
    assert status.ok is True
    assert status.latency_ms >= 0


def test_health_check_error():
    class _Pool:
        def acquire(self) -> MagicMock:
            raise RuntimeError("db down")

    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=_Pool())
    status = asyncio.run(provider.health_check())
    assert status.ok is False
    assert "db down" in status.detail


# ── _fetch_raw_a / _fetch_raw_b ───────────────────────────────────────────────


def test_fetch_raw_a_patient_not_found():
    class _Conn:
        async def fetchrow(self, *_: Any):
            return None

        async def fetch(self, *_: Any):
            return []

    with pytest.raises(ConnectorDataError, match="not found in institution A"):
        asyncio.run(_fetch_raw_a(_Conn(), "MISSING"))


def test_fetch_raw_b_patient_not_found():
    class _Conn:
        async def fetchrow(self, *_: Any):
            return None

        async def fetch(self, *_: Any):
            return []

    with pytest.raises(ConnectorDataError, match="not found in institution B"):
        asyncio.run(_fetch_raw_b(_Conn(), "MISSING"))


def test_fetch_raw_a_returns_dict_rows():
    """asyncpg Record objects are converted to plain dicts."""
    mock_row = {"patient_id": "P1", "date_of_birth": "1950-01-01", "sex": "F"}
    mock_dx = {
        "diagnosis_id": "D1",
        "patient_id": "P1",
        "icd10_code": "I10",
        "description": "HTN",
        "status": "active",
    }

    call_count = 0

    class _Conn:
        async def fetchrow(self, *_: Any):
            return mock_row

        async def fetch(self, sql: str, *_: Any):
            nonlocal call_count
            call_count += 1
            if "diagnoses" in sql:
                return [mock_dx]
            return []

    patient_row, related = asyncio.run(_fetch_raw_a(_Conn(), "P1"))
    assert isinstance(patient_row, dict)
    assert patient_row["patient_id"] == "P1"
    assert isinstance(related["diagnoses"], list)
    assert related["diagnoses"][0]["icd10_code"] == "I10"


# ── _get_pool lazy creation ───────────────────────────────────────────────────


def test_get_pool_creates_asyncpg_pool_lazily():
    """When no pool is injected, _get_pool imports asyncpg and creates a pool."""
    import sys
    from unittest.mock import patch

    fake_pool = MagicMock()
    fake_asyncpg = MagicMock()
    fake_asyncpg.create_pool = AsyncMock(return_value=fake_pool)

    provider = PostgresProvider(dsn="postgresql://x/db", institution="a")
    with patch.dict(sys.modules, {"asyncpg": fake_asyncpg}):
        pool = asyncio.run(provider._get_pool())

    assert pool is fake_pool
    fake_asyncpg.create_pool.assert_awaited_once_with("postgresql://x/db", min_size=1, max_size=3)
    # Second call returns cached pool without re-creating
    pool2 = asyncio.run(provider._get_pool())
    assert pool2 is fake_pool
    assert fake_asyncpg.create_pool.await_count == 1


# ── mapper helpers: valid-R4B value/status (review fix-forward) ───────────────


class TestMapperHelpers:
    def test_value_quantity_with_unit_sets_ucum(self) -> None:
        vq = _value_quantity(5.0, "mg/dL")
        assert vq == {
            "value": 5.0,
            "unit": "mg/dL",
            "system": "http://unitsofmeasure.org",
            "code": "mg/dL",
        }

    def test_value_quantity_without_unit_omits_system_and_code(self) -> None:
        # Missing unit must NOT emit code:'' alongside a populated system (invalid R4B).
        vq = _value_quantity(5.0, None)
        assert vq == {"value": 5.0}
        assert "system" not in vq and "code" not in vq
        assert _value_quantity(7.0, "") == {"value": 7.0}

    def test_value_quantity_no_unit_passes_r4b_validation(self) -> None:
        from fhir.resources.R4B.observation import Observation

        obs = {
            "resourceType": "Observation",
            "id": "o1",
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "x"}]},
            "valueQuantity": _value_quantity(5.0, None),
        }
        # Would raise if valueQuantity carried code:'' with a populated system.
        assert Observation.model_validate(obs).valueQuantity.value == 5.0

    def test_observation_status_passthrough_and_coercion(self) -> None:
        assert _observation_status("final") == "final"
        assert _observation_status("amended") == "amended"
        assert _observation_status(None) == "final"
        # Institution B's overloaded status_flag (e.g. an RX 'active') is not a
        # valid ObservationStatus → coerce to 'final'.
        assert _observation_status("active") == "final"
        assert _observation_status("STOPPED") == "final"
