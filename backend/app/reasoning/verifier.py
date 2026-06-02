"""Citation verifier (REASON-02 cache-authoritative layer).

Post-Gemini safety gate: every citation in a DecisionPacket is re-checked
against the actual cache.  Any hypothesis with an unresolvable or
unsupported citation is dropped.  If nothing survives, the packet abstains
rather than inventing an answer.

This is intentionally plain, synchronous code with no AI involvement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from backend.app.dtos import Citation, DecisionPacket, Hypothesis, Span

# ── Callable types ────────────────────────────────────────────────────────────

ResourceLookup = Callable[[str, str, str], "dict | None"]
"""(patient_id, resource_type, resource_id) → resource dict or None."""

EvidenceLookup = Callable[[str], "dict | None"]
"""(evidence_id) → evidence card dict or None."""

PdfPageLookup = Callable[[int], "str | None"]
"""(page_number) → page text or None.  Only used when an evidence card
carries a ``span`` field pointing into a source PDF."""

# ── Citation kinds that the verifier knows how to check ──────────────────────

_EVIDENCE_KINDS = frozenset({"evidence", "evidence_card"})
_RESOURCE_KINDS = frozenset({"resource"})

# ── Abstention message ────────────────────────────────────────────────────────

ABSTAIN_MESSAGE = "No well-supported explanation found."


# ── Internal result type ──────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DropReason:
    """Why a hypothesis was dropped.  Attached to the hypothesis id for logs."""

    citation_ref: str
    reason: str


# ── Public API ────────────────────────────────────────────────────────────────


def verify_packet(
    packet: DecisionPacket,
    *,
    resource_lookup: ResourceLookup,
    evidence_lookup: EvidenceLookup,
    pdf_pages: PdfPageLookup | None = None,
) -> DecisionPacket:
    """Return a new DecisionPacket with unverifiable hypotheses removed.

    Parameters
    ----------
    packet:
        The AI-produced packet to validate.
    resource_lookup:
        Callable that fetches a patient FHIR resource from the cache.
        Should wrap ``cache.store.get_patient_resource``.
    evidence_lookup:
        Callable that fetches an evidence card from the cache.
        Should wrap ``cache.store.get_evidence_card``.
    pdf_pages:
        Optional callable returning extracted page text by page number.
        When provided, evidence cards that carry a ``span`` field are
        checked against the source text (PDF-quote integrity).

    Returns
    -------
    DecisionPacket
        A new packet.  ``hypotheses`` contains only verified entries.
        If none survive, ``summary_markdown`` is set to the abstention
        message and ``hypotheses`` is empty.
    """
    kept: list[Hypothesis] = []

    for hyp in packet.hypotheses:
        drop = _check_hypothesis(
            hyp,
            patient_id=packet.patient_id,
            resource_lookup=resource_lookup,
            evidence_lookup=evidence_lookup,
            pdf_pages=pdf_pages,
        )
        if drop is None:
            kept.append(
                _enrich_hypothesis(
                    hyp,
                    patient_id=packet.patient_id,
                    resource_lookup=resource_lookup,
                )
            )

    if not kept:
        return DecisionPacket(
            patient_id=packet.patient_id,
            summary_markdown=ABSTAIN_MESSAGE,
            hypotheses=[],
            data_gaps=list(packet.data_gaps),
            completeness=list(packet.completeness),
            cache_status=packet.cache_status,
        )

    return DecisionPacket(
        patient_id=packet.patient_id,
        summary_markdown=packet.summary_markdown,
        hypotheses=kept,
        data_gaps=list(packet.data_gaps),
        completeness=list(packet.completeness),
        cache_status=packet.cache_status,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────


def _check_hypothesis(
    hyp: Hypothesis,
    *,
    patient_id: str,
    resource_lookup: ResourceLookup,
    evidence_lookup: EvidenceLookup,
    pdf_pages: PdfPageLookup | None,
) -> DropReason | None:
    """Return None if every citation checks out, DropReason otherwise."""
    for citation in hyp.citations:
        reason = _check_citation(
            citation,
            patient_id=patient_id,
            resource_lookup=resource_lookup,
            evidence_lookup=evidence_lookup,
            pdf_pages=pdf_pages,
        )
        if reason is not None:
            return reason
    return None


def _enrich_hypothesis(
    hyp: Hypothesis,
    *,
    patient_id: str,
    resource_lookup: ResourceLookup,
) -> Hypothesis:
    """Attach the PDF ``source_span`` to every resolvable resource citation.

    Runs only on hypotheses that already passed verification, so the lookups
    here are guaranteed to resolve. A resource that carries no ``span`` (e.g. a
    non-PDF FHIR record) keeps ``source_span=None``, which the frontend renders
    as a non-interactive chip — never "looks clickable but does nothing".
    """
    enriched: list[Citation] = []
    changed = False
    for citation in hyp.citations:
        span = _span_for_resource(citation, patient_id=patient_id, resource_lookup=resource_lookup)
        if span is None:
            enriched.append(citation)
            continue
        enriched.append(citation.model_copy(update={"source_span": span}))
        changed = True
    if not changed:
        return hyp
    return hyp.model_copy(update={"citations": enriched})


def _span_for_resource(
    citation: Citation,
    *,
    patient_id: str,
    resource_lookup: ResourceLookup,
) -> Span | None:
    """Return the source ``Span`` for a PDF-sourced resource citation, else None."""
    if citation.kind.lower() not in _RESOURCE_KINDS:
        return None
    parts = citation.ref.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    resource = resource_lookup(patient_id, parts[0], parts[1])
    if resource is None:
        return None
    span = resource.get("span")
    if not isinstance(span, dict):
        return None
    return Span(
        page=span["page"],
        start=span["start"],
        end=span["end"],
        snippet=span["snippet"],
    )


def _check_citation(
    citation: Citation,
    *,
    patient_id: str,
    resource_lookup: ResourceLookup,
    evidence_lookup: EvidenceLookup,
    pdf_pages: PdfPageLookup | None,
) -> DropReason | None:
    kind = citation.kind.lower()

    if kind in _RESOURCE_KINDS:
        return _check_resource(citation, patient_id=patient_id, resource_lookup=resource_lookup)

    if kind in _EVIDENCE_KINDS:
        return _check_evidence(citation, evidence_lookup=evidence_lookup, pdf_pages=pdf_pages)

    return DropReason(
        citation_ref=citation.ref,
        reason=f"Unknown citation kind {citation.kind!r} — cannot verify",
    )


def _check_resource(
    citation: Citation,
    *,
    patient_id: str,
    resource_lookup: ResourceLookup,
) -> DropReason | None:
    parts = citation.ref.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return DropReason(
            citation_ref=citation.ref,
            reason=f"Malformed resource ref {citation.ref!r} — expected ResourceType/id",
        )
    resource_type, resource_id = parts
    if resource_lookup(patient_id, resource_type, resource_id) is None:
        return DropReason(
            citation_ref=citation.ref,
            reason=f"Patient resource {citation.ref!r} not found in cache",
        )
    return None


def _check_evidence(
    citation: Citation,
    *,
    evidence_lookup: EvidenceLookup,
    pdf_pages: PdfPageLookup | None,
) -> DropReason | None:
    card = evidence_lookup(citation.ref)
    if card is None:
        return DropReason(
            citation_ref=citation.ref,
            reason=f"Evidence card {citation.ref!r} not found",
        )

    snippet = card.get("snippet") or ""
    if not snippet.strip():
        return DropReason(
            citation_ref=citation.ref,
            reason=f"Evidence card {citation.ref!r} has no backing snippet",
        )

    # PDF-quote integrity: if the card carries a span and we have page text,
    # the snippet must literally appear at [start:end] in the source.
    span = card.get("span")
    if span and pdf_pages is not None:
        page_text = pdf_pages(span["page"]) or ""
        actual = page_text[span["start"] : span["end"]]
        if actual != span["snippet"]:
            return DropReason(
                citation_ref=citation.ref,
                reason=(
                    f"PDF quote mismatch for {citation.ref!r}: "
                    f"source has {actual!r}, span claims {span['snippet']!r}"
                ),
            )

    return None
