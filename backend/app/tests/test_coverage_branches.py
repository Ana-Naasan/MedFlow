"""Branch-coverage tests for the correctness-critical core.

Targets the renderer/helper branches in fhir.flatten, the not-found branches in
cache.store, the edge cases in fhir.subset minimisation, the error paths in the
HL7v2 connector, and the abstract Provider methods — driving the core packages
(fhir, providers, cache, knowledge) to 100% line coverage.
"""

from __future__ import annotations

import asyncio
import datetime

import pytest

from backend.app.cache.store import (
    build_packet,
    get_evidence_card,
    get_evidence_cards,
    get_patient_resource,
    get_patient_resources,
)
from backend.app.fhir.flatten import (
    _concept,
    _date,
    _dose,
    _first_code,
    _is_nka,
    _nested,
    _obs_value,
    _render,
    flatten_to_tagged_text,
)
from backend.app.fhir.subset import reasoning_view
from backend.app.providers.base import (
    Capability,
    ConnectorDataError,
    FetchResult,
    HealthStatus,
    Provider,
)
from backend.app.providers.hl7v2 import HL7v2Provider

# ── fhir.flatten renderers (via the public entry point) ─────────────────────


def _line_for(resource: dict) -> str:
    """Return the rendered line for a single resource from the tagged output."""
    rid = resource.get("id", "unknown")
    tag = f"[{resource['resourceType']}/{rid}]"
    for line in flatten_to_tagged_text([resource]).splitlines():
        if line.startswith(tag):
            return line
    raise AssertionError(f"no line for {tag}")


def test_render_medication_with_dose() -> None:
    med = {
        "resourceType": "MedicationStatement",
        "id": "m1",
        "status": "active",
        "medicationCodeableConcept": {"text": "Aspirin"},
        "dosage": [{"doseAndRate": [{"doseQuantity": {"value": 81, "unit": "mg"}}]}],
    }
    assert _line_for(med) == "[MedicationStatement/m1] Aspirin 81 mg — active"


def test_render_condition_with_statuses() -> None:
    cond = {
        "resourceType": "Condition",
        "id": "c1",
        "code": {"text": "Hypertension"},
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "verificationStatus": {"coding": [{"code": "confirmed"}]},
    }
    assert _line_for(cond) == "[Condition/c1] Hypertension — active, confirmed"


def test_render_observation_with_value_and_date() -> None:
    obs = {
        "resourceType": "Observation",
        "id": "o1",
        "code": {"text": "Systolic BP"},
        "valueQuantity": {"value": 120, "unit": "mmHg"},
        "effectiveDateTime": "2024-06-15T10:30:00Z",
    }
    assert _line_for(obs) == "[Observation/o1] Systolic BP: 120 mmHg (2024-06-15)"


def test_render_observation_date_from_period() -> None:
    obs = {
        "resourceType": "Observation",
        "id": "o2",
        "code": {"text": "HR"},
        "valueString": "irregular",
        "effectivePeriod": {"start": "2024-01-02T00:00:00Z"},
    }
    assert _line_for(obs) == "[Observation/o2] HR: irregular (2024-01-02)"


def test_render_allergy_non_nka() -> None:
    allergy = {
        "resourceType": "AllergyIntolerance",
        "id": "a1",
        "code": {"text": "Penicillin"},
        "clinicalStatus": {"coding": [{"code": "active"}]},
    }
    assert _line_for(allergy) == "[AllergyIntolerance/a1] Penicillin — active"


def test_render_procedure_with_date() -> None:
    proc = {
        "resourceType": "Procedure",
        "id": "p1",
        "code": {"text": "Appendectomy"},
        "status": "completed",
        "performedPeriod": {"start": "2023-03-03T08:00:00Z"},
    }
    assert _line_for(proc) == "[Procedure/p1] Appendectomy — completed (2023-03-03)"


def test_render_unknown_type_fallback() -> None:
    assert _render("Unknown", {"resourceType": "Unknown"}) == "Unknown"


# ── fhir.flatten helpers (direct) ───────────────────────────────────────────


def test_concept_variants() -> None:
    assert _concept(None) == ""
    assert _concept({"text": "T"}) == "T"
    assert _concept({"coding": [{"display": "D"}]}) == "D"
    assert _concept({"coding": [{"code": "C"}]}) == "C"
    assert _concept({"coding": []}) == ""


def test_first_code_variants() -> None:
    assert _first_code(None) == ""
    assert _first_code({"coding": []}) == ""
    assert _first_code({"coding": [{"code": "x"}]}) == "x"


def test_nested_non_dict_midpath() -> None:
    assert _nested({"a": "scalar"}, "a", "b") is None
    assert _nested({"a": {"b": "v"}}, "a", "b") == "v"
    assert _nested({"a": {"b": 5}}, "a", "b") is None  # non-str leaf


def test_date_variants() -> None:
    assert _date(None) == ""
    assert _date("2024-12-31T23:59:59Z") == " (2024-12-31)"


def test_dose_variants() -> None:
    assert _dose({}) == ""
    assert _dose({"dosage": [{}]}) == ""
    assert _dose({"dosage": [{"doseAndRate": [{"doseQuantity": {}}]}]}) == ""
    full = {"dosage": [{"doseAndRate": [{"doseQuantity": {"value": 5, "unit": "mg"}}]}]}
    assert _dose(full) == " 5 mg"
    # value present but unit absent → trailing space stripped
    no_unit = {"dosage": [{"doseAndRate": [{"doseQuantity": {"value": 5}}]}]}
    assert _dose(no_unit) == " 5"
    # no structured quantity → fall back to the free-text dosage line
    assert _dose({"dosage": [{"text": "5 mg oral daily"}]}) == " (5 mg oral daily)"


def test_obs_value_variants() -> None:
    assert _obs_value({"valueQuantity": {"value": 7, "unit": "x"}}) == "7 x"
    assert _obs_value({"valueString": "s"}) == "s"
    assert _obs_value({"valueCodeableConcept": {"text": "cc"}}) == "cc"
    assert _obs_value({}) == ""


def test_is_nka_non_allergy() -> None:
    assert _is_nka("Condition", {}) is False


# ── cache.store not-found branches ──────────────────────────────────────────


def test_get_patient_resource_unknown_patient() -> None:
    assert get_patient_resource("nope", "Patient", "x") is None


def test_get_patient_resource_unknown_resource() -> None:
    assert get_patient_resource("pat-001", "Patient", "missing") is None


def test_get_evidence_card_unknown() -> None:
    assert get_evidence_card("does-not-exist") is None


def test_build_packet_demo_001_returns_hypotheses() -> None:
    packet = build_packet("DEMO-001")
    assert packet.patient_id == "DEMO-001"
    assert len(packet.hypotheses) >= 1
    assert len(packet.completeness) >= 1


def test_build_packet_demo_001_applies_gap_downgrade() -> None:
    """Issue #30: demo medication-citing hypotheses are downgraded one step because
    the patient record has no Allergy or Observation resources (safety-critical gaps)."""
    packet = build_packet("DEMO-001")

    def _cites_med(h: object) -> bool:
        return any(
            c.kind == "resource" and c.ref.startswith("MedicationStatement/")
            for c in h.citations  # type: ignore[attr-defined]
        )

    med_citing = [h for h in packet.hypotheses if _cites_med(h)]
    assert med_citing, "expected at least one medication-citing hypothesis in the demo"
    for h in med_citing:
        assert h.confidence == "medium", (
            f"hypothesis {h.id} should be downgraded high → medium due to safety-critical gaps "
            f"(Allergies, Labs), got confidence={h.confidence!r}"
        )


def test_build_packet_default_has_completeness() -> None:
    packet = build_packet("pat-001")
    assert len(packet.completeness) >= 1
    categories = [c.category for c in packet.completeness]
    assert "Patient" in categories
    assert "Medications" in categories


def test_get_evidence_card_demo_001_evidence_resolvable() -> None:
    # Evidence cards keyed under DEMO-001 must resolve now that the lookup
    # iterates all patients rather than hard-coding pat-001 as the anchor.
    card = get_evidence_card("ddinter-warfarin-aspirin")
    assert card is not None
    assert card["id"] == "ddinter-warfarin-aspirin"


def test_get_patient_resource_with_span() -> None:
    resource = get_patient_resource("DEMO-001", "MedicationStatement", "med-warfarin")
    assert resource is not None
    assert "span" in resource
    span = resource["span"]
    assert span["page"] == 2  # type: ignore[index]
    assert "snippet" in span  # type: ignore[operator]


def test_get_evidence_card_missing_anchor_patient(monkeypatch: pytest.MonkeyPatch) -> None:
    # When STATIC_PATIENTS is empty the loop produces nothing → None.
    import backend.app.cache.store as store

    monkeypatch.setattr(store, "STATIC_PATIENTS", {})
    assert store.get_evidence_card("anything") is None


def test_get_patient_resources_returns_resource_dicts() -> None:
    resources = get_patient_resources("pat-001")
    assert isinstance(resources, list)
    assert any(r["resourceType"] == "MedicationStatement" for r in resources)


def test_get_patient_resources_unknown_patient() -> None:
    assert get_patient_resources("nope") == []


def test_get_evidence_cards_returns_card_dicts() -> None:
    cards = get_evidence_cards("pat-001")
    assert isinstance(cards, list)
    assert any(c["id"] == "ddinter-aspirin-warfarin" for c in cards)


def test_get_evidence_cards_unknown_patient() -> None:
    assert get_evidence_cards("nope") == []


# ── fhir.subset reasoning_view edge cases ───────────────────────────────────


def test_reasoning_view_birthdate_as_date_object() -> None:
    view = reasoning_view(
        {"resourceType": "Patient", "id": "p", "birthDate": datetime.date(1950, 1, 1)}
    )
    assert isinstance(view["ageYears"], int)
    assert "birthDate" not in view


def test_reasoning_view_birthdate_invalid_string() -> None:
    view = reasoning_view({"resourceType": "Patient", "id": "p", "birthDate": "nope"})
    assert "ageYears" not in view
    assert "birthDate" not in view


def test_reasoning_view_birthdate_wrong_type() -> None:
    view = reasoning_view({"resourceType": "Patient", "id": "p", "birthDate": 1950})
    assert "ageYears" not in view


def test_reasoning_view_identifier_non_dict_entries() -> None:
    # identifier entries that are not MRN dicts get filtered out
    view = reasoning_view(
        {
            "resourceType": "Patient",
            "id": "p",
            "identifier": [
                "not-a-dict",
                {"value": "x"},  # no type
                {"value": "y", "type": "not-a-dict"},  # type not dict
                {"value": "z", "type": {"coding": "not-a-list"}},  # coding not list
            ],
        }
    )
    assert "identifier" not in view  # none were MRN


# ── providers.hl7v2 error paths ─────────────────────────────────────────────


def test_hl7v2_no_pid_segment_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the parsed message to have a .pid whose .to_er7() raises, exercising
    # the "No PID segment" branch in _parse_adt.
    import backend.app.providers.hl7v2 as mod

    class _NoPid:
        @property
        def pid(self):  # noqa: ANN202
            raise AttributeError("no PID")

    monkeypatch.setattr(mod, "parse_message", lambda *a, **k: _NoPid())
    provider = HL7v2Provider(raw_message="MSH|...")
    with pytest.raises(ConnectorDataError):
        asyncio.run(provider.fetch_patient("pat-001"))


def test_hl7v2_generic_exception_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force _parse_adt to raise a non-ConnectorDataError; fetch_patient must wrap it.
    import backend.app.providers.hl7v2 as mod

    def boom(_raw: str) -> dict:
        raise ValueError("unexpected")

    monkeypatch.setattr(mod, "_parse_adt", boom)
    provider = HL7v2Provider(raw_message="anything")
    with pytest.raises(ConnectorDataError):
        asyncio.run(provider.fetch_patient("pat-001"))


def test_hl7v2_invalid_message_raises() -> None:
    provider = HL7v2Provider(raw_message="not a valid hl7 message at all")
    with pytest.raises(ConnectorDataError):
        asyncio.run(provider.fetch_patient("pat-001"))


# ── providers.base abstract methods ─────────────────────────────────────────


class _BareProvider(Provider):
    id = "bare"
    capabilities = Capability.PATIENT

    async def fetch_patient(self, patient_id: str) -> FetchResult:
        return await super().fetch_patient(patient_id)

    async def health_check(self) -> HealthStatus:
        return await super().health_check()


def test_base_abstract_methods_raise() -> None:
    bare = _BareProvider()
    with pytest.raises(NotImplementedError):
        asyncio.run(bare.fetch_patient("x"))
    with pytest.raises(NotImplementedError):
        asyncio.run(bare.health_check())
