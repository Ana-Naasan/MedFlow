"""Tests for the decision-packet orchestrator (reasoning/pipeline.py).

build_reasoned_packet wires run_reasoning into a servable DecisionPacket and
falls back to the static scaffold on any abstention (empty output, missing
GOOGLE_GENAI_API_KEY, or the cache-authoritative verifier dropping everything).
run_reasoning is mocked here — its internals are covered by test_reasoning_core.
"""

from __future__ import annotations

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
