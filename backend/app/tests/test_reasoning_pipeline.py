"""Tests for the decision-packet orchestrator (reasoning/pipeline.py).

build_reasoned_packet wires run_reasoning into a servable DecisionPacket and
falls back to the static scaffold on any abstention (empty output, missing
GOOGLE_GENAI_API_KEY, or the cache-authoritative verifier dropping everything).
run_reasoning is mocked here — its internals are covered by test_reasoning_core.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from backend.app.dtos import CategoryCompleteness, Citation, DecisionPacket, Hypothesis
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning import pipeline
from backend.app.reasoning.pipeline import REASONED_SUMMARY, build_reasoned_packet

_PATIENT_ID = "p1"


def _scaffold() -> DecisionPacket:
    return DecisionPacket(
        patient_id=_PATIENT_ID,
        summary_markdown="STATIC SUMMARY",
        hypotheses=[
            Hypothesis(
                id="static-1",
                title="Static hypothesis",
                why="Static fallback content.",
                severity="moderate",
                confidence="low",
                citations=[Citation(kind="resource", ref="MedicationStatement/med-1", label=None)],
            )
        ],
        data_gaps=["a gap"],
        completeness=[
            CategoryCompleteness(category="Labs", documented=False, gap_note="connect labs")
        ],
        cache_status=None,
    )


_RESOURCES = [
    {
        "resourceType": "MedicationStatement",
        "id": "med-1",
        "status": "active",
        "medicationCodeableConcept": {"text": "Aspirin"},
        "subject": {"reference": "Patient/p1"},
    }
]
_EVIDENCE = [EvidenceSnippet(id="ev-1", kind="evidence", ref="ev-1", label="Some evidence")]


def _resource_lookup(patient_id: str, resource_type: str, resource_id: str) -> dict | None:
    if (patient_id, resource_type, resource_id) == (_PATIENT_ID, "MedicationStatement", "med-1"):
        return {"resourceType": "MedicationStatement", "id": "med-1"}
    return None


def _evidence_lookup(ref: str) -> dict | None:
    if ref == "ev-1":
        return {"id": "ev-1", "snippet": "Some evidence text."}
    return None


def _reasoned_hypothesis(resource_ref: str = "MedicationStatement/med-1") -> Hypothesis:
    return Hypothesis(
        id="live-1",
        title="Aspirin may be associated with bleeding risk",
        why="The record lists aspirin and an evidence card notes bleeding risk.",
        severity="moderate",
        confidence="low",
        citations=[
            Citation(kind="resource", ref=resource_ref, label="Aspirin"),
            Citation(kind="evidence", ref="ev-1", label="Some evidence"),
        ],
    )


async def _call(monkeypatch: pytest.MonkeyPatch, run_reasoning_mock: object) -> DecisionPacket:
    monkeypatch.setattr(pipeline, "run_reasoning", run_reasoning_mock)
    return await build_reasoned_packet(
        _scaffold(),
        _RESOURCES,
        _EVIDENCE,
        resource_lookup=_resource_lookup,
        evidence_lookup=_evidence_lookup,
    )


@pytest.mark.asyncio
async def test_serves_live_hypotheses_when_reasoning_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = await _call(monkeypatch, AsyncMock(return_value=[_reasoned_hypothesis()]))
    assert packet.summary_markdown == REASONED_SUMMARY
    assert [h.id for h in packet.hypotheses] == ["live-1"]


@pytest.mark.asyncio
async def test_preserves_scaffold_completeness_on_live_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # verify_packet rebuilds the packet WITHOUT completeness — the orchestrator
    # must restore it from the scaffold.
    packet = await _call(monkeypatch, AsyncMock(return_value=[_reasoned_hypothesis()]))
    assert [c.category for c in packet.completeness] == ["Labs"]


@pytest.mark.asyncio
async def test_live_med_hypothesis_downgraded_when_safety_critical_data_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # REASON-06 / #30: a live model hypothesis citing a medication must have its
    # confidence downgraded one step when the patient record has no labs
    # (Observation) or allergies (AllergyIntolerance) — never claim safety from
    # absence. _RESOURCES holds only a MedicationStatement, so both
    # safety-critical categories are absent and a 'high' must become 'medium'.
    high_conf = _reasoned_hypothesis().model_copy(update={"confidence": "high"})
    packet = await _call(monkeypatch, AsyncMock(return_value=[high_conf]))
    assert [h.id for h in packet.hypotheses] == ["live-1"]
    assert packet.hypotheses[0].confidence == "medium"


@pytest.mark.asyncio
async def test_live_hypothesis_not_downgraded_when_labs_and_allergies_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The downgrade is data-driven: when the record DOES document labs and
    # allergies, a 'high' med hypothesis stays 'high' (no spurious downgrade).
    resources = [
        *_RESOURCES,
        {"resourceType": "Observation", "id": "obs-1"},
        {"resourceType": "AllergyIntolerance", "id": "alg-1"},
    ]
    monkeypatch.setattr(
        pipeline,
        "run_reasoning",
        AsyncMock(return_value=[_reasoned_hypothesis().model_copy(update={"confidence": "high"})]),
    )
    packet = await build_reasoned_packet(
        _scaffold(),
        resources,
        _EVIDENCE,
        resource_lookup=_resource_lookup,
        evidence_lookup=_evidence_lookup,
    )
    assert packet.hypotheses[0].confidence == "high"


@pytest.mark.asyncio
async def test_falls_back_to_scaffold_when_reasoning_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    packet = await _call(monkeypatch, AsyncMock(return_value=[]))
    assert packet.summary_markdown == "STATIC SUMMARY"
    assert [h.id for h in packet.hypotheses] == ["static-1"]


@pytest.mark.asyncio
async def test_falls_back_to_scaffold_when_api_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # _get_client raises KeyError outside run_reasoning's try/except when the key
    # is unset; the orchestrator must treat that as abstention, not a crash.
    packet = await _call(monkeypatch, AsyncMock(side_effect=KeyError("GOOGLE_GENAI_API_KEY")))
    assert packet.summary_markdown == "STATIC SUMMARY"
    assert [h.id for h in packet.hypotheses] == ["static-1"]


@pytest.mark.asyncio
async def test_falls_back_to_scaffold_when_reasoning_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #90: the live Gemini call runs in /packet's request path. A slow/hung call
    # (cold ~10-20s, or worse) must NOT block the page until it gives up
    # ("Failed to load packet"). The orchestrator bounds reasoning and abstains to
    # the citation-safe scaffold once REASONING_TIMEOUT_SECONDS is exceeded.
    async def _slow(*_args: object, **_kwargs: object) -> list:
        await asyncio.sleep(0.5)
        return [_reasoned_hypothesis()]

    monkeypatch.setattr(pipeline, "REASONING_TIMEOUT_SECONDS", 0.01)
    packet = await _call(monkeypatch, _slow)
    assert packet.summary_markdown == "STATIC SUMMARY"
    assert [h.id for h in packet.hypotheses] == ["static-1"]


@pytest.mark.asyncio
async def test_falls_back_when_verifier_drops_every_hypothesis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Reasoning returns a hypothesis citing an UNRESOLVABLE resource — the
    # cache-authoritative verify_packet drops it, so the orchestrator abstains.
    bad = _reasoned_hypothesis(resource_ref="MedicationStatement/does-not-exist")
    packet = await _call(monkeypatch, AsyncMock(return_value=[bad]))
    assert packet.summary_markdown == "STATIC SUMMARY"
    assert [h.id for h in packet.hypotheses] == ["static-1"]


@pytest.mark.asyncio
async def test_fallback_verifies_scaffold_and_abstains_on_unresolvable_citation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The fallback must run the scaffold through the cache-authoritative gate too:
    # a scaffold citing a resource that does not resolve must NOT be served raw
    # (the no-unresolvable-citation invariant applies to the static path as well).
    bad_scaffold = _scaffold().model_copy(
        update={
            "hypotheses": [
                Hypothesis(
                    id="bad",
                    title="t",
                    why="w",
                    severity="moderate",
                    confidence="low",
                    citations=[
                        Citation(kind="resource", ref="MedicationStatement/ghost", label=None)
                    ],
                )
            ]
        }
    )
    monkeypatch.setattr(pipeline, "run_reasoning", AsyncMock(return_value=[]))
    packet = await build_reasoned_packet(
        bad_scaffold,
        _RESOURCES,
        _EVIDENCE,
        resource_lookup=_resource_lookup,
        evidence_lookup=_evidence_lookup,
    )
    assert packet.hypotheses == []
