"""Compute real drug-knowledge evidence for the live reasoning path.

Replaces the hand-authored ``STATIC_PATIENTS`` evidence scaffold: given a
patient's FHIR resources, this module normalizes medications (RxNav) and gathers
cited evidence from openFDA / DDInter / Beers / ACB so ``/packet`` reasons over
*real* sources. Each source is isolated so an exhausted API token or a transient
failure simply contributes no cards — the packet stays citation-safe.

The single canonical citation key is ``EvidenceSnippet.id``: the model cites it,
the persisted evidence_card store is keyed by it, and the deterministic verifier
resolves it. Every emitted card carries a non-empty ``snippet`` (the verifier
drops cards without one).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from backend.app.dtos import EvidenceSnippet
from backend.app.fhir.flatten import _concept
from backend.app.fhir.subset import _compute_age_years
from backend.app.knowledge import openfda, rxnav
from backend.app.knowledge.acb import lookup_acb
from backend.app.knowledge.beers import lookup_beers
from backend.app.knowledge.ddinter import find_interactions

_T = TypeVar("_T")

_OPENFDA_SOURCE = "openFDA"
_DDINTER_SOURCE = "DDInter"
_DDINTER_URL = "https://ddinter.scbdd.com/"
_BEERS_SOURCE = "AGS Beers Criteria 2023"
_BEERS_URL = "https://agsjournals.onlinelibrary.wiley.com/doi/10.1111/jgs.18372"
_ACB_SOURCE = "ACB Scale"
_ACB_URL = "https://www.acbcalc.com/"


@dataclass
class KnowledgeEvidence:
    """The computed knowledge evidence for one patient.

    ``snippets`` is the citation allow-list handed to the reasoning core;
    ``cards`` mirrors it as ``{id, source, snippet, ref_url, kind}`` dicts for
    the evidence_card store + ``/evidence`` + the verifier; ``resolution_report``
    drives KNOW-01 unresolved-flagging and the REASON-07 min-input contract.
    """

    snippets: list[EvidenceSnippet] = field(default_factory=list)
    cards: list[dict] = field(default_factory=list)
    resolution_report: rxnav.DrugResolutionReport = field(
        default_factory=rxnav.DrugResolutionReport
    )


def extract_medication_names(resources):
    """Return deduped medication display names from ``MedicationStatement`` resources.

    Reads each statement's ``medicationCodeableConcept`` via the flattener's
    ``_concept`` (text → coding display → coding code), preserves first-seen
    order, and dedupes case-insensitively. Non-medication resources, non-dict
    entries, and blank names are skipped.
    """
    seen: set[str] = set()
    names: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("resourceType") != "MedicationStatement":
            continue
        name = _concept(resource.get("medicationCodeableConcept")).strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def patient_age_years(resources) -> int | None:
    """Derive the patient's age in whole years from the Patient resource's
    ``birthDate`` (SEC-02: age from DOB), or ``None`` when unavailable."""
    for resource in resources:
        if isinstance(resource, dict) and resource.get("resourceType") == "Patient":
            return _compute_age_years(resource.get("birthDate"))
    return None


def _safe_call(fn: Callable[[], _T]) -> _T | None:
    """Run a sync knowledge lookup, returning ``None`` if it raises — so an
    unavailable source contributes nothing instead of breaking the packet."""
    try:
        return fn()
    except Exception:
        return None


async def _safe_await(coro: Awaitable[_T]) -> _T | None:
    """Await an async knowledge lookup, returning ``None`` if it raises
    (openFDA timeout / exhausted token / unexpected error)."""
    try:
        return await coro
    except Exception:
        return None


def _openfda_ref_url(kind: str, rxcui: str | None) -> str:
    endpoint = "event" if kind.startswith("openfda_adverse") else "label"
    return f"https://api.fda.gov/drug/{endpoint}.json?search=openfda.rxcui:{rxcui or ''}"


async def build_knowledge_evidence(resources, age_years: int | None) -> KnowledgeEvidence:
    """Compute cited drug-knowledge evidence for a patient's resources.

    Normalizes meds via RxNav (KNOW-01), then gathers openFDA adverse-event +
    label evidence per resolved drug (KNOW-02), DDInter pairwise interactions
    (KNOW-03), Beers geriatric PIMs (KNOW-04, age-gated), and ACB anticholinergic
    burden (KNOW-05). Returns deduped snippets + parallel card dicts + the
    resolution report. Each source is isolated; a failing source is simply
    skipped.
    """
    names = extract_medication_names(resources)

    report = _safe_call(lambda: rxnav.resolve_drugs(names))
    if report is None:
        report = rxnav.DrugResolutionReport(
            resolutions=[rxnav.DrugResolution(input_name=n, network_error=True) for n in names]
        )

    collected: list[tuple[EvidenceSnippet, str, str]] = []

    # openFDA — one combined adverse-event + label lookup per resolved drug.
    for resolution in report.resolutions:
        if not resolution.resolved:
            continue
        rxcui = resolution.rxcui or resolution.ingredient_rxcui
        result = await _safe_await(
            openfda.lookup_drug(rxcui=rxcui, generic_name=resolution.name or resolution.input_name)
        )
        if result is None:
            continue
        for snippet in result.evidence_snippets:
            collected.append((snippet, _OPENFDA_SOURCE, _openfda_ref_url(snippet.kind, rxcui)))

    # DDInter — pairwise interactions across the resolved drugs.
    for interaction in _safe_call(lambda: find_interactions(report.resolutions)) or []:
        snippet = EvidenceSnippet(
            id=interaction.evidence_id,
            kind="ddinter_interaction",
            ref=interaction.evidence_id,
            label=interaction.snippet,
        )
        collected.append((snippet, _DDINTER_SOURCE, _DDINTER_URL))

    # Beers geriatric PIMs (age-gated; age unknown => not assessed, no cards).
    beers = _safe_call(lambda: lookup_beers(names, age_years))
    for snippet in beers.snippets if beers else []:
        collected.append((snippet, _BEERS_SOURCE, snippet.ref or _BEERS_URL))

    # ACB anticholinergic burden.
    acb = _safe_call(lambda: lookup_acb(names, age_years))
    for snippet in acb.snippets if acb else []:
        collected.append((snippet, _ACB_SOURCE, snippet.ref or _ACB_URL))

    # Dedupe by the canonical id, preserving first occurrence; build the parallel
    # snippet allow-list + card dicts together so the store and allow-list stay 1:1.
    seen: set[str] = set()
    snippets: list[EvidenceSnippet] = []
    cards: list[dict[str, Any]] = []
    for snippet, source, ref_url in collected:
        if snippet.id in seen:
            continue
        seen.add(snippet.id)
        snippets.append(snippet)
        cards.append(
            {
                "id": snippet.id,
                "source": source,
                "snippet": snippet.label,
                "ref_url": ref_url,
                "kind": snippet.kind,
            }
        )

    return KnowledgeEvidence(snippets=snippets, cards=cards, resolution_report=report)
