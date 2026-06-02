"""Tests for reasoning/verifier.py — REASON-02 cache-authoritative safety gate.

All tests are pure-unit: lookups are lambda stubs, no DB or network required.
"""

from __future__ import annotations

import pytest

from backend.app.dtos import (
    CategoryCompleteness,
    Citation,
    DecisionPacket,
    Hypothesis,
)
from backend.app.reasoning.verifier import (
    ABSTAIN_MESSAGE,
    DropReason,
    _span_for_resource,
    verify_packet,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

_PATIENT_ID = "pat-001"

_GOOD_RESOURCE = {"resourceType": "Patient", "id": "pat-001"}
_RESOURCE_SPAN = {"page": 2, "start": 143, "end": 183, "snippet": "Warfarin 5 mg oral"}
_RESOURCE_WITH_SPAN = {
    "resourceType": "MedicationStatement",
    "id": "med-warfarin",
    "span": _RESOURCE_SPAN,
}
_GOOD_EVIDENCE = {"id": "ev-001", "source": "DDInter", "snippet": "Drug X increases bleeding risk."}
_EVIDENCE_WITH_SPAN = {
    "id": "ev-span",
    "source": "pdf",
    "snippet": "warfarin aspirin",
    "span": {"page": 1, "start": 0, "end": 16, "snippet": "warfarin aspirin"},
}

_NO_RESOURCE: dict = {}  # sentinel — lookup returns None when this is used


def _resource_returns(resource: dict | None):
    return lambda *_: resource


def _evidence_returns(card: dict | None):
    return lambda _: card


def _make_packet(hypotheses: list[Hypothesis], **kwargs) -> DecisionPacket:
    return DecisionPacket(
        patient_id=_PATIENT_ID,
        summary_markdown="## Test packet",
        hypotheses=hypotheses,
        data_gaps=["some gap"],
        cache_status="HIT",
        **kwargs,
    )


def _make_hyp(citations: list[Citation], hyp_id: str = "hyp-001") -> Hypothesis:
    return Hypothesis(
        id=hyp_id,
        title="Test hypothesis",
        why="Because reasons.",
        severity="moderate",
        confidence="low",
        citations=citations,
    )


def _resource_citation(ref: str = "Patient/pat-001") -> Citation:
    return Citation(kind="resource", ref=ref, label=ref)


def _evidence_citation(ref: str = "ev-001") -> Citation:
    return Citation(kind="evidence", ref=ref, label=ref)


# ── Happy path ────────────────────────────────────────────────────────────────


def test_valid_packet_passes_through_unchanged() -> None:
    hyp = _make_hyp([_resource_citation(), _evidence_citation()])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert len(result.hypotheses) == 1
    assert result.hypotheses[0].id == "hyp-001"
    assert result.summary_markdown == packet.summary_markdown


def test_data_gaps_preserved_on_success() -> None:
    hyp = _make_hyp([_evidence_citation()])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.data_gaps == ["some gap"]


def test_cache_status_preserved_on_success() -> None:
    hyp = _make_hyp([_evidence_citation()])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.cache_status == "HIT"


# ── Required issue tests ──────────────────────────────────────────────────────


def test_fake_citation_dropped() -> None:
    """Evidence ref that doesn't exist → hypothesis dropped."""
    hyp = _make_hyp([_evidence_citation("nonexistent-evidence-id")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(None),  # fake — returns nothing
    )
    assert result.hypotheses == []


def test_broken_patient_reference_dropped() -> None:
    """Resource citation that doesn't exist in cache → hypothesis dropped."""
    hyp = _make_hyp([_resource_citation("Patient/ghost-patient")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(None),  # broken — patient not in cache
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses == []


def test_abstain_when_none_survive() -> None:
    """All hypotheses fail → abstention message, empty hypotheses."""
    hyp1 = _make_hyp([_evidence_citation("fake-1")], hyp_id="hyp-001")
    hyp2 = _make_hyp([_evidence_citation("fake-2")], hyp_id="hyp-002")
    packet = _make_packet([hyp1, hyp2])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(None),
    )
    assert result.hypotheses == []
    assert result.summary_markdown == ABSTAIN_MESSAGE


def test_abstain_preserves_data_gaps() -> None:
    hyp = _make_hyp([_evidence_citation("fake")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(None),
        evidence_lookup=_evidence_returns(None),
    )
    assert result.data_gaps == ["some gap"]


def test_abstain_preserves_cache_status() -> None:
    hyp = _make_hyp([_evidence_citation("fake")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(None),
        evidence_lookup=_evidence_returns(None),
    )
    assert result.cache_status == "HIT"


# ── Multi-hypothesis: partial survival ────────────────────────────────────────


def test_good_hypothesis_survives_when_bad_one_dropped() -> None:
    good = _make_hyp([_evidence_citation("ev-001")], hyp_id="good")
    bad = _make_hyp([_evidence_citation("fake")], hyp_id="bad")
    packet = _make_packet([good, bad])

    def evidence_lookup(ref: str) -> dict | None:
        return _GOOD_EVIDENCE if ref == "ev-001" else None

    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=evidence_lookup,
    )
    assert len(result.hypotheses) == 1
    assert result.hypotheses[0].id == "good"


# ── Malformed refs ────────────────────────────────────────────────────────────


def test_malformed_resource_ref_no_slash_dropped() -> None:
    hyp = _make_hyp([Citation(kind="resource", ref="PatientWithoutSlash")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses == []


def test_malformed_resource_ref_empty_type_dropped() -> None:
    hyp = _make_hyp([Citation(kind="resource", ref="/just-id")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses == []


def test_malformed_resource_ref_empty_id_dropped() -> None:
    hyp = _make_hyp([Citation(kind="resource", ref="Patient/")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses == []


# ── Unknown citation kind ─────────────────────────────────────────────────────


def test_unknown_citation_kind_dropped() -> None:
    hyp = _make_hyp([Citation(kind="mystery_kind", ref="something")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses == []


def test_evidence_card_kind_alias_accepted() -> None:
    """'evidence_card' is an accepted alias for 'evidence'."""
    hyp = _make_hyp([Citation(kind="evidence_card", ref="ev-001")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert len(result.hypotheses) == 1


# ── Snippet validation ────────────────────────────────────────────────────────


def test_evidence_card_with_empty_snippet_dropped() -> None:
    empty_snippet_card = {"id": "ev-001", "source": "DDInter", "snippet": ""}
    hyp = _make_hyp([_evidence_citation()])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(empty_snippet_card),
    )
    assert result.hypotheses == []


def test_evidence_card_with_whitespace_only_snippet_dropped() -> None:
    card = {"id": "ev-001", "source": "DDInter", "snippet": "   "}
    hyp = _make_hyp([_evidence_citation()])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(card),
    )
    assert result.hypotheses == []


def test_evidence_card_with_missing_snippet_key_dropped() -> None:
    card = {"id": "ev-001", "source": "DDInter"}  # no snippet key
    hyp = _make_hyp([_evidence_citation()])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(card),
    )
    assert result.hypotheses == []


# ── PDF span checks ───────────────────────────────────────────────────────────


def test_evidence_with_matching_span_passes() -> None:
    """Span snippet matches page_text[start:end] → passes."""
    page_text = "warfarin aspirin interaction note"
    hyp = _make_hyp([Citation(kind="evidence", ref="ev-span")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_EVIDENCE_WITH_SPAN),
        pdf_pages=lambda page: page_text if page == 1 else None,
    )
    assert len(result.hypotheses) == 1


def test_evidence_with_mismatched_span_dropped() -> None:
    """page_text[start:end] doesn't match span snippet → dropped."""
    wrong_page = "COMPLETELY DIFFERENT TEXT HERE!!!"
    hyp = _make_hyp([Citation(kind="evidence", ref="ev-span")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_EVIDENCE_WITH_SPAN),
        pdf_pages=lambda page: wrong_page if page == 1 else None,
    )
    assert result.hypotheses == []


def test_evidence_with_span_but_no_pdf_pages_passes() -> None:
    """When pdf_pages is None, span check is skipped — card still passes."""
    hyp = _make_hyp([Citation(kind="evidence", ref="ev-span")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_EVIDENCE_WITH_SPAN),
        pdf_pages=None,
    )
    assert len(result.hypotheses) == 1


# ── Empty packet ──────────────────────────────────────────────────────────────


def test_empty_hypotheses_returns_abstention() -> None:
    packet = _make_packet([])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses == []
    assert result.summary_markdown == ABSTAIN_MESSAGE


# ── Mixed citation in one hypothesis ─────────────────────────────────────────


def test_hypothesis_with_one_bad_citation_among_good_ones_dropped() -> None:
    """All-or-nothing: one bad citation drops the whole hypothesis."""
    hyp = _make_hyp(
        [
            _resource_citation("Patient/pat-001"),  # good
            _evidence_citation("fake-id"),  # bad
        ]
    )
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(None),
    )
    assert result.hypotheses == []


# ── DropReason public type ────────────────────────────────────────────────────


def test_drop_reason_is_frozen() -> None:
    dr = DropReason(citation_ref="X/1", reason="test")
    with pytest.raises((AttributeError, TypeError)):
        dr.citation_ref = "Y/2"  # type: ignore[misc]


# ── completeness propagation (issue #30 / #87) ───────────────────────────────
#
# verify_packet rebuilds the DecisionPacket on BOTH the keep path and the
# abstain path. The `completeness` list must survive both — it carries the
# "unknown ≠ none" data-gap signal to the UI, so silently dropping it would make
# a partial record look complete. These tests fail if either rebuild stops
# copying `completeness`.

_COMPLETENESS = [
    CategoryCompleteness(category="Allergies", documented=False, gap_note="not documented"),
    CategoryCompleteness(category="Medications", documented=True),
]


def test_completeness_preserved_on_keep_path() -> None:
    hyp = _make_hyp([_resource_citation()])
    packet = _make_packet([hyp], completeness=_COMPLETENESS)
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert len(result.hypotheses) == 1  # sanity: this is the keep path
    assert result.completeness == _COMPLETENESS


def test_completeness_preserved_on_abstain_path() -> None:
    hyp = _make_hyp([_resource_citation("Patient/ghost-patient")])
    packet = _make_packet([hyp], completeness=_COMPLETENESS)
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(None),  # all citations unresolvable
        evidence_lookup=_evidence_returns(None),
    )
    assert result.hypotheses == []  # sanity: this is the abstain path
    assert result.summary_markdown == ABSTAIN_MESSAGE
    assert result.completeness == _COMPLETENESS


# ── source_span enrichment (#97) ─────────────────────────────────────────────
#
# A verified PDF-sourced resource citation must carry its source_span so the
# frontend can render the highlight view. A resource with no span (or a
# non-resource citation) keeps source_span=None and the chip stays static.


def test_resource_citation_gets_source_span_when_pdf_sourced() -> None:
    hyp = _make_hyp([_resource_citation("MedicationStatement/med-warfarin")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_RESOURCE_WITH_SPAN),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert len(result.hypotheses) == 1
    span = result.hypotheses[0].citations[0].source_span
    assert span is not None
    assert span.page == 2
    assert span.start == 143
    assert span.end == 183
    assert span.snippet == "Warfarin 5 mg oral"


def test_resource_citation_without_span_stays_none() -> None:
    hyp = _make_hyp([_resource_citation("Patient/pat-001")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_GOOD_RESOURCE),  # no span key
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert len(result.hypotheses) == 1
    assert result.hypotheses[0].citations[0].source_span is None


def test_evidence_citation_never_gets_source_span() -> None:
    hyp = _make_hyp([_evidence_citation("ev-001")])
    packet = _make_packet([hyp])
    result = verify_packet(
        packet,
        resource_lookup=_resource_returns(_RESOURCE_WITH_SPAN),
        evidence_lookup=_evidence_returns(_GOOD_EVIDENCE),
    )
    assert result.hypotheses[0].citations[0].source_span is None


def test_span_for_resource_ignores_non_resource_kind() -> None:
    span = _span_for_resource(
        _evidence_citation("ev-001"),
        patient_id=_PATIENT_ID,
        resource_lookup=_resource_returns(_RESOURCE_WITH_SPAN),
    )
    assert span is None


def test_span_for_resource_handles_malformed_ref() -> None:
    span = _span_for_resource(
        Citation(kind="resource", ref="NoSlash"),
        patient_id=_PATIENT_ID,
        resource_lookup=_resource_returns(_RESOURCE_WITH_SPAN),
    )
    assert span is None


def test_span_for_resource_handles_missing_resource() -> None:
    span = _span_for_resource(
        _resource_citation("MedicationStatement/ghost"),
        patient_id=_PATIENT_ID,
        resource_lookup=_resource_returns(None),
    )
    assert span is None


def test_span_for_resource_ignores_non_dict_span() -> None:
    resource = {"resourceType": "MedicationStatement", "id": "x", "span": "not-a-dict"}
    span = _span_for_resource(
        _resource_citation("MedicationStatement/x"),
        patient_id=_PATIENT_ID,
        resource_lookup=_resource_returns(resource),
    )
    assert span is None
