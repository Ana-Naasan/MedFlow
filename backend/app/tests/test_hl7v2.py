"""Tests for HL7v2 ADT scaffold connector."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    FetchResult,
    HealthStatus,
)
from backend.app.providers.hl7v2 import HL7v2Provider, _parse_adt

_ADT_A01 = (
    "MSH|^~\\&|HOSP|FAC|RECV|RECV|20260530120000||ADT^A01|MSG001|P|2.5\r"
    "EVN|A01|20260530120000\r"
    "PID|1||PAT001^^^FAC^MR||Romaguera^Kent^^^^^L||19400109|M\r"
    "PV1|1|I|WARD3B\r"
)

_ADT_FEMALE = (
    "MSH|^~\\&|HOSP|FAC|RECV|RECV|20260530120000||ADT^A01|MSG002|P|2.5\r"
    "EVN|A01|20260530120000\r"
    "PID|1||PAT002^^^FAC^MR||Jones^Mary^^^^^L||19550315|F\r"
    "PV1|1|I|WARD1\r"
)


# ── _parse_adt unit tests ─────────────────────────────────────────────────────


def test_parse_adt_returns_patient_resource() -> None:
    patient = _parse_adt(_ADT_A01)
    assert patient["resourceType"] == "Patient"


def test_parse_adt_extracts_patient_id() -> None:
    patient = _parse_adt(_ADT_A01)
    assert patient["id"] == "PAT001"


def test_parse_adt_extracts_family_name() -> None:
    patient = _parse_adt(_ADT_A01)
    names = patient.get("name", [])
    assert names, "name list must not be empty"
    assert names[0]["family"] == "Romaguera"


def test_parse_adt_extracts_given_name() -> None:
    patient = _parse_adt(_ADT_A01)
    names = patient.get("name", [])
    assert names
    assert "Kent" in names[0].get("given", [])


def test_parse_adt_extracts_gender_male() -> None:
    patient = _parse_adt(_ADT_A01)
    assert patient["gender"] == "male"


def test_parse_adt_extracts_birth_date() -> None:
    patient = _parse_adt(_ADT_A01)
    assert patient.get("birthDate") == "1940-01-09"


def test_parse_adt_female_gender() -> None:
    patient = _parse_adt(_ADT_FEMALE)
    assert patient["gender"] == "female"


def test_parse_adt_invalid_message_raises_connector_data_error() -> None:
    with pytest.raises(ConnectorDataError):
        _parse_adt("this is not hl7")


# ── HL7v2Provider integration tests ──────────────────────────────────────────


def test_provider_id_is_hl7v2() -> None:
    assert HL7v2Provider.id == "hl7v2"


def test_provider_supports_patient_capability() -> None:
    provider = HL7v2Provider(_ADT_A01)
    assert provider.supports(Capability.PATIENT)


def test_fetch_patient_returns_fetch_result() -> None:
    provider = HL7v2Provider(_ADT_A01)
    result = asyncio.run(provider.fetch_patient("PAT001"))
    assert isinstance(result, FetchResult)


def test_fetch_patient_bundle_is_fhir_bundle() -> None:
    provider = HL7v2Provider(_ADT_A01)
    result = asyncio.run(provider.fetch_patient("PAT001"))
    bundle = result.bundle
    assert isinstance(bundle, dict)
    assert bundle["resourceType"] == "Bundle"
    assert len(bundle.get("entry", [])) >= 1


def test_fetch_patient_result_is_partial() -> None:
    provider = HL7v2Provider(_ADT_A01)
    result = asyncio.run(provider.fetch_patient("PAT001"))
    assert result.partial is True


def test_fetch_patient_has_scaffold_warning() -> None:
    provider = HL7v2Provider(_ADT_A01)
    result = asyncio.run(provider.fetch_patient("PAT001"))
    assert len(result.warnings) >= 1
    combined = " ".join(result.warnings).lower()
    assert "scaffold" in combined or "roadmap" in combined


def test_fetch_patient_coverage_patient_returned_true() -> None:
    provider = HL7v2Provider(_ADT_A01)
    result = asyncio.run(provider.fetch_patient("PAT001"))
    assert result.coverage.get("patient", {}).get("returned") is True


def test_fetch_patient_coverage_medications_returned_false() -> None:
    provider = HL7v2Provider(_ADT_A01)
    result = asyncio.run(provider.fetch_patient("PAT001"))
    assert result.coverage.get("medications", {}).get("returned") is False


def test_health_check_returns_health_status() -> None:
    provider = HL7v2Provider(_ADT_A01)
    status = asyncio.run(provider.health_check())
    assert isinstance(status, HealthStatus)
    assert status.ok is True


def test_health_check_never_raises_on_bad_message() -> None:
    provider = HL7v2Provider("garbage input")
    status = asyncio.run(provider.health_check())
    assert isinstance(status, HealthStatus)


def test_fetch_patient_raises_connector_data_error_on_invalid_hl7() -> None:
    provider = HL7v2Provider("this is not hl7")
    with pytest.raises(ConnectorDataError):
        asyncio.run(provider.fetch_patient("xxx"))
