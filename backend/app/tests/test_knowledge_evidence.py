"""Tests for reasoning/knowledge_evidence.py — wiring the drug-knowledge layer
into the live reasoning path.

Increment 1: extract_medication_names — pull deduped medication display names
from a patient's FHIR resources so the knowledge lookups (RxNav/openFDA/DDInter/
Beers/ACB) have something to key on.
"""

from __future__ import annotations

import httpx
import pytest

from backend.app.knowledge import rxnav
from backend.app.reasoning.knowledge_evidence import (
    build_knowledge_evidence,
    extract_medication_names,
    patient_age_years,
)


def _med(concept: dict) -> dict:
    return {"resourceType": "MedicationStatement", "medicationCodeableConcept": concept}


def test_extracts_name_from_codeable_concept_text():
    resources = [_med({"text": "Warfarin"})]
    assert extract_medication_names(resources) == ["Warfarin"]


def test_falls_back_to_coding_display_then_code():
    resources = [
        _med({"coding": [{"display": "Aspirin 81 MG Oral Tablet"}]}),
        _med({"coding": [{"code": "1191"}]}),
    ]
    assert extract_medication_names(resources) == ["Aspirin 81 MG Oral Tablet", "1191"]


def test_ignores_non_medication_resources_and_non_dicts():
    resources = [
        {"resourceType": "Condition", "code": {"text": "Atrial fibrillation"}},
        {"resourceType": "Patient", "id": "p1"},
        None,  # defensive: non-dict entries are skipped
        _med({"text": "Amitriptyline"}),
    ]
    assert extract_medication_names(resources) == ["Amitriptyline"]


def test_skips_blank_concepts():
    resources = [_med({}), _med({"text": ""}), _med({"text": "Metformin"})]
    assert extract_medication_names(resources) == ["Metformin"]


def test_dedupes_case_insensitively_preserving_first_seen_order():
    resources = [
        _med({"text": "Aspirin"}),
        _med({"text": "Warfarin"}),
        _med({"text": "aspirin"}),  # duplicate of the first, different case
    ]
    assert extract_medication_names(resources) == ["Aspirin", "Warfarin"]


def test_empty_resources_yields_empty_list():
    assert extract_medication_names([]) == []


# ── patient_age_years ─────────────────────────────────────────────────────────


def test_patient_age_years_from_birthdate():
    resources = [{"resourceType": "Patient", "id": "p", "birthDate": "1942-03-15"}]
    age = patient_age_years(resources)
    assert age is not None and age >= 65


def test_patient_age_years_none_when_no_patient_or_no_dob():
    assert patient_age_years([_med({"text": "Aspirin"})]) is None
    assert patient_age_years([{"resourceType": "Patient", "id": "p"}]) is None


# ── build_knowledge_evidence ──────────────────────────────────────────────────

_PATIENT = {"resourceType": "Patient", "id": "p", "birthDate": "1942-03-15"}
_RESOURCES = [
    _PATIENT,
    _med({"text": "Warfarin"}),
    _med({"text": "Aspirin"}),
    _med({"text": "Amitriptyline"}),
]


def _res(name: str, rxcui: str | None = None, resolved: bool = True) -> rxnav.DrugResolution:
    return rxnav.DrugResolution(
        input_name=name,
        rxcui=rxcui,
        name=name,
        resolved=resolved,
        match_quality="exact" if resolved else "failed",
    )


@pytest.mark.asyncio
async def test_build_knowledge_evidence_happy_path(monkeypatch, mock_openfda):
    # RxNav is stubbed (no live HTTP); openFDA served by the offline mock;
    # DDInter/Beers/ACB run for real against the vendored seeds.
    monkeypatch.setattr(
        rxnav,
        "resolve_drugs",
        lambda names: rxnav.DrugResolutionReport(
            resolutions=[
                _res("Warfarin", "11289"),
                _res("Aspirin", "1191"),
                _res("Acetylsalicylic acid", "1191"),  # same rxcui → dup openFDA ids → dedup
                _res("Amitriptyline", "704"),
                _res("Unobtainium", resolved=False),  # exercises the unresolved-skip path
            ]
        ),
    )
    age = patient_age_years(_RESOURCES)
    ke = await build_knowledge_evidence(_RESOURCES, age)

    ids = {s.id for s in ke.snippets}
    # snippets and cards stay 1:1 by id, deduped (openFDA emits the same ids per drug)
    assert len(ke.snippets) == len(ke.cards) == len(ids)
    # every card carries a non-empty snippet — the verifier drops cards without one
    assert all(c["snippet"] for c in ke.cards)
    # all four knowledge sources contributed real cited evidence
    assert any(i.startswith("openfda") for i in ids)
    assert any(i.startswith("ddinter-") for i in ids)
    assert any(i.startswith("beers:") for i in ids)
    assert any(i.startswith("acb:") for i in ids)
    assert {"openFDA", "DDInter", "AGS Beers Criteria 2023", "ACB Scale"} <= {
        c["source"] for c in ke.cards
    }
    # the resolution report flows through, including the unresolved drug (KNOW-01)
    assert ke.resolution_report.failed_count == 1


@pytest.mark.asyncio
async def test_rxnav_failure_falls_back_but_beers_acb_still_run(monkeypatch, mock_openfda):
    def _boom(_names):
        raise RuntimeError("rxnav unreachable")

    monkeypatch.setattr(rxnav, "resolve_drugs", _boom)
    ke = await build_knowledge_evidence(_RESOURCES, 84)

    # Fallback report: nothing resolved, every med flagged as a network error.
    assert ke.resolution_report.resolved_count == 0
    assert all(r.network_error for r in ke.resolution_report.resolutions)
    # openFDA + DDInter need resolved drugs → contribute nothing; Beers/ACB key on
    # the raw names so they still surface cards.
    ids = {s.id for s in ke.snippets}
    assert all(not i.startswith("openfda") for i in ids)
    assert any(i.startswith("beers:") or i.startswith("acb:") for i in ids)


@pytest.mark.asyncio
async def test_openfda_failure_skips_only_openfda(monkeypatch, mock_openfda_factory):
    monkeypatch.setattr(
        rxnav,
        "resolve_drugs",
        lambda names: rxnav.DrugResolutionReport(resolutions=[_res("Amitriptyline", "704")]),
    )

    def _unreachable(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("openFDA unreachable (token exhausted)")

    mock_openfda_factory(_unreachable)
    ke = await build_knowledge_evidence(_RESOURCES, 84)

    ids = {s.id for s in ke.snippets}
    # A transport failure (e.g. exhausted token) drops only openFDA; ACB still runs.
    assert all(not i.startswith("openfda") for i in ids)
    assert any(i.startswith("acb:") for i in ids)
