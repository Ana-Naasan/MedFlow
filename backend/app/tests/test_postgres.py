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
    _allergy_clinical_status,
    _fetch_raw_a,
    _fetch_raw_b,
    _iso_date,
    _observation_status,
    _procedure_status,
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


# ── #67 honesty/fidelity: status value-set mappers ────────────────────────────


class TestAllergyClinicalStatusMapper:
    """Maps Institution B's status_flag onto the R4B clinicalStatus value set."""

    def test_passes_through_valid_codes(self) -> None:
        assert _allergy_clinical_status("active") == "active"
        assert _allergy_clinical_status("inactive") == "inactive"
        assert _allergy_clinical_status("resolved") == "resolved"

    def test_case_insensitive_and_trims(self) -> None:
        assert _allergy_clinical_status("  Active ") == "active"
        assert _allergy_clinical_status("RESOLVED") == "resolved"

    def test_unknown_token_defaults_active(self) -> None:
        # We never silently drop an allergy — default to the safer 'active'
        # rather than coercing to an invalid code.
        assert _allergy_clinical_status("foo") == "active"
        assert _allergy_clinical_status("") == "active"

    def test_none_defaults_active(self) -> None:
        # Mirrors Institution A's behaviour (no status column → assume active).
        assert _allergy_clinical_status(None) == "active"


class TestProcedureStatusMapper:
    """Maps Institution B's status_flag onto the R4B Procedure.status value set."""

    def test_passes_through_valid_codes(self) -> None:
        for code in (
            "preparation",
            "in-progress",
            "not-done",
            "on-hold",
            "stopped",
            "completed",
            "entered-in-error",
            "unknown",
        ):
            assert _procedure_status(code) == code

    def test_synonyms_map_to_valid_codes(self) -> None:
        assert _procedure_status("active") == "in-progress"
        assert _procedure_status("ongoing") == "in-progress"
        assert _procedure_status("done") == "completed"
        assert _procedure_status("finished") == "completed"
        assert _procedure_status("cancelled") == "stopped"
        assert _procedure_status("canceled") == "stopped"
        assert _procedure_status("aborted") == "stopped"

    def test_unknown_token_does_not_overstate_completed(self) -> None:
        # The previous behaviour hard-coded 'completed' for every procedure —
        # now unknown tokens map to 'unknown' so we don't overclaim.
        assert _procedure_status("garbage") == "unknown"

    def test_none_defaults_completed_for_a_compatibility(self) -> None:
        # Institution A has no status column; absence preserves A's historical
        # "everything in procedures_done is completed" assumption.
        assert _procedure_status(None) == "completed"


# ── #67 honesty/fidelity: birthDate normalization ────────────────────────────


class TestIsoDateNormalizer:
    """A's date_of_birth (asyncpg DATE → date) and B's dob (VARCHAR → str)
    must serialise identically. _iso_date is the single source of truth."""

    def test_date_object_serialises_iso(self) -> None:
        import datetime as _dt

        assert _iso_date(_dt.date(1950, 3, 15)) == "1950-03-15"

    def test_datetime_object_drops_time(self) -> None:
        import datetime as _dt

        assert _iso_date(_dt.datetime(1950, 3, 15, 12, 30)) == "1950-03-15"

    def test_string_passthrough_after_strip(self) -> None:
        assert _iso_date("1950-03-15") == "1950-03-15"
        assert _iso_date("  1950-03-15  ") == "1950-03-15"

    def test_empty_string_collapses_to_none(self) -> None:
        assert _iso_date("") is None
        assert _iso_date("   ") is None

    def test_none_is_none(self) -> None:
        assert _iso_date(None) is None

    def test_other_types_stringified(self) -> None:
        # Defensive: a column with an unexpected type still produces a value
        # rather than crashing the fetch.
        assert _iso_date(19500315) == "19500315"


def test_a_and_b_produce_birthdate_identically() -> None:
    """A returns date_of_birth as asyncpg DATE → datetime.date; B as VARCHAR
    → str. Both must serialise to the same ISO string after _iso_date."""
    import datetime as _dt

    res_a, _ = _translate_a(
        {"patient_id": "X", "sex": "M", "date_of_birth": _dt.date(1950, 3, 15)},
        {},
    )
    res_b, _ = _translate_b(
        {"pt_ref": "X", "gender_code": "M", "dob": "1950-03-15"},
        [],
    )
    assert res_a[0]["birthDate"] == res_b[0]["birthDate"] == "1950-03-15"


# ── #67 tests bullet: full A==B equivalence across all 6 types ────────────────


def test_a_and_b_produce_identical_fhir_for_all_six_types() -> None:
    """Stronger than the per-field A==B checks: every resource type produced
    by the two translators must be structurally equivalent (modulo per-row
    ids, which are schema-specific) for the same clinical profile."""
    res_a, _ = _translate_a(_IA_PATIENT, _IA_RELATED)
    res_b, _ = _translate_b(_IB_PATIENT, _IB_EVENTS)

    def _normalize(r: dict) -> dict:
        c = dict(r)
        # Per-row ids differ by schema; the rest of the structure must match.
        c.pop("id", None)
        return c

    by_type_a = {r["resourceType"]: _normalize(r) for r in res_a}
    by_type_b = {r["resourceType"]: _normalize(r) for r in res_b}
    expected = {
        "Patient",
        "Condition",
        "MedicationStatement",
        "Observation",
        "AllergyIntolerance",
        "Procedure",
    }
    assert set(by_type_a) == expected
    assert set(by_type_b) == expected
    for rtype in expected:
        assert by_type_a[rtype] == by_type_b[rtype], (
            f"{rtype} structure differs between Institution A and Institution B:\n"
            f"A: {by_type_a[rtype]}\nB: {by_type_b[rtype]}"
        )


# ── #67 honesty/fidelity: partial flag honesty ────────────────────────────────


def test_supported_but_empty_capability_appends_warning_and_flips_partial() -> None:
    """When the connector advertises a capability but no records come back for
    it, the FetchResult must say so (warning + partial=True) — absence is
    not the same as "patient has none" (issue #30/#67)."""

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **_: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, *_: Any):
            return {"patient_id": _PATIENT_ID, "date_of_birth": "1950-03-15", "sex": "F"}

        async def fetch(self, *_: Any) -> list:
            return []  # No conditions, meds, labs, allergies, procedures.

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

    assert result.partial is True
    assert any(
        "No records returned for supported categories" in w for w in result.warnings
    ), result.warnings
    # And every supported-but-empty capability is named in the warning:
    warning = next(w for w in result.warnings if "No records" in w)
    for cap in ("allergies", "conditions", "medications", "observations", "procedures"):
        assert cap in warning, warning


def test_complete_fetch_appends_no_warning_and_stays_not_partial() -> None:
    """When every supported capability returns ≥1 record, no honesty-warning
    is added and partial stays False."""

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    # Pre-mapped lookups so a single _Conn handles every SELECT path.
    related = _IA_RELATED

    class _Conn:
        def transaction(self, **_: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, sql: str, *args: Any):
            return {"patient_id": _PATIENT_ID, "date_of_birth": "1950-03-15", "sex": "F"}

        async def fetch(self, sql: str, *args: Any) -> list:
            sql_l = sql.lower()
            if "diagnoses" in sql_l:
                return related["diagnoses"]
            if "prescriptions" in sql_l:
                return related["prescriptions"]
            if "lab_results" in sql_l:
                return related["lab_results"]
            if "allergies" in sql_l:
                return related["allergies"]
            if "procedures" in sql_l:
                return related["procedures"]
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

    assert result.partial is False
    assert not any("No records returned" in w for w in result.warnings)
    # Every supported capability reports returned=True:
    for cap in (
        "patient",
        "conditions",
        "medications",
        "observations",
        "allergies",
        "procedures",
    ):
        assert result.coverage[cap]["returned"] is True, result.coverage


def test_coverage_keys_track_capabilities_not_a_hardcoded_set() -> None:
    """coverage keys derive from self.capabilities. A provider that drops a
    capability (e.g. PROCEDURES) must NOT advertise that capability as
    requested in the coverage dict (#67 — never claim safety from absence)."""

    class _Txn:
        async def __aenter__(self) -> _Txn:
            return self

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class _Conn:
        def transaction(self, **_: Any) -> _Txn:
            return _Txn()

        async def fetchrow(self, *_: Any):
            return {"patient_id": _PATIENT_ID, "date_of_birth": "1950-03-15", "sex": "F"}

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
    # Narrow capabilities: drop ALLERGIES and PROCEDURES.
    from backend.app.providers.base import Capability

    provider.capabilities = Capability.PATIENT | Capability.CONDITIONS | Capability.MEDICATIONS
    result = asyncio.run(provider.fetch_patient(_PATIENT_ID))

    # Dropped capabilities are absent from coverage entirely (not "requested
    # but not returned" — that would dishonestly suggest we tried).
    assert "allergies" not in result.coverage
    assert "procedures" not in result.coverage
    assert set(result.coverage.keys()) == {"patient", "conditions", "medications"}


# ── #67 robustness: _get_pool lock ────────────────────────────────────────────


def test_get_pool_creates_pool_only_once_under_concurrency() -> None:
    """Two concurrent fetch_patient calls on a cold provider must share the
    same pool — without the asyncio.Lock the loser leaks its create_pool()."""

    provider = PostgresProvider(dsn="postgresql://x", institution="a")
    create_calls = {"count": 0}

    async def _fake_create_pool(dsn: str, *, min_size: int, max_size: int) -> object:
        create_calls["count"] += 1
        # Yield to the loop so a racing coroutine can see _pool is still None.
        await asyncio.sleep(0)
        return object()

    import sys
    import types

    fake_asyncpg = types.SimpleNamespace(create_pool=_fake_create_pool)
    sys.modules["asyncpg"] = fake_asyncpg  # type: ignore[assignment]
    try:

        async def _race() -> None:
            pools = await asyncio.gather(
                provider._get_pool(),
                provider._get_pool(),
                provider._get_pool(),
            )
            assert pools[0] is pools[1] is pools[2]

        asyncio.run(_race())
    finally:
        sys.modules.pop("asyncpg", None)

    assert create_calls["count"] == 1, (
        f"asyncpg.create_pool was called {create_calls['count']} times; "
        "expected exactly 1 under the asyncio.Lock guard."
    )


def test_get_pool_returns_injected_pool_without_creating() -> None:
    """The injected-pool fast path must NOT take the lock or import asyncpg."""

    sentinel = object()
    provider = PostgresProvider(dsn="postgresql://x", institution="a", pool=sentinel)
    got = asyncio.run(provider._get_pool())
    assert got is sentinel
