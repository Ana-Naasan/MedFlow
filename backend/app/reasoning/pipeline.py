"""Decision-packet orchestration: the production caller for the reasoning core.

Without this module ``run_reasoning`` would have no production caller — the
"primary online guardrail" would run on zero requests. This module is that
caller. It flattens the patient's FHIR resources, runs the Gemini reasoning
core (which self-verifies citations against the prompt context and applies the
output-language guard), then re-checks every surviving citation against the
cache (the cache-authoritative ``verify_packet``).

Demo-safety / REASON-08 abstention: if reasoning yields nothing servable —
empty output, a transient Gemini failure, a missing ``GOOGLE_GENAI_API_KEY``, or
the cache-authoritative gate dropping every hypothesis — the provided static
``scaffold`` is returned unchanged, so ``/packet`` always serves a
citation-safe packet.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from backend.app.config import REASONING_TIMEOUT_SECONDS
from backend.app.dtos import DecisionPacket
from backend.app.fhir.data_gaps import apply_gap_downgrades, live_gap_fhir_types
from backend.app.fhir.flatten import flatten_to_tagged_text
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.core import DEFAULT_MODEL, run_reasoning
from backend.app.reasoning.verifier import (
    EvidenceLookup,
    PdfPageLookup,
    ResourceLookup,
    verify_packet,
)

# Neutral associational header for the live path. The static scaffold's summary
# describes its own hardcoded hypotheses, so it must not be reused verbatim over
# model-generated ones (which would misdescribe them).
REASONED_SUMMARY = (
    "Cited considerations for clinician review — each may be associated with the "
    "patient's record; open a citation to verify the source."
)


async def build_reasoned_packet(
    scaffold: DecisionPacket,
    resources: Sequence[dict],
    evidence: Sequence[EvidenceSnippet],
    *,
    resource_lookup: ResourceLookup,
    evidence_lookup: EvidenceLookup,
    pdf_pages: PdfPageLookup | None = None,
    model: str = DEFAULT_MODEL,
) -> DecisionPacket:
    """Run live reasoning over a patient, falling back to ``scaffold`` on abstention.

    Parameters
    ----------
    scaffold:
        The static DecisionPacket (summary / data_gaps / completeness +
        guaranteed-safe hypotheses) served if reasoning produces nothing.
    resources:
        The patient's FHIR resource dicts (flattened into the prompt context).
    evidence:
        Knowledge snippets whose ids form the evidence-citation allow-list.
    resource_lookup / evidence_lookup / pdf_pages:
        Cache-authoritative lookups for the post-generation ``verify_packet`` gate.
    """
    flattened = flatten_to_tagged_text(resources)

    def _verified_scaffold() -> DecisionPacket:
        # The no-unresolvable-citation invariant applies to the fallback too: a
        # non-static (e.g. intake) patient's default scaffold can carry a citation
        # that does not resolve for them, so run the scaffold through the
        # cache-authoritative gate rather than serving it raw. If nothing resolves
        # it abstains (citation-free). verify_packet already preserves
        # completeness, so the surviving-hypotheses branch returns it directly.
        return verify_packet(
            scaffold,
            resource_lookup=resource_lookup,
            evidence_lookup=evidence_lookup,
            pdf_pages=pdf_pages,
        )

    try:
        async with asyncio.timeout(REASONING_TIMEOUT_SECONDS):
            hypotheses = await run_reasoning(flattened, evidence, model=model)
    except Exception:
        # REASON-08 / always-servable guarantee: ANY reasoning failure abstains to
        # the citation-safe scaffold rather than 500-ing. run_reasoning builds the
        # client + prompt OUTSIDE its own try/except (a missing GOOGLE_GENAI_API_KEY
        # raises KeyError; the SDK can raise TimeoutError / ValueError /
        # ValidationError), so the guard here must be broad. The asyncio.timeout
        # above bounds the call (#90): a slow/hung Gemini call inside /packet's
        # request path raises TimeoutError here instead of blocking until the page
        # gives up. The scaffold path is still citation-gated below, so abstaining
        # never weakens the safety bar.
        hypotheses = []

    if not hypotheses:
        return _verified_scaffold()

    candidate = scaffold.model_copy(
        update={"hypotheses": hypotheses, "summary_markdown": REASONED_SUMMARY}
    )
    verified = verify_packet(
        candidate,
        resource_lookup=resource_lookup,
        evidence_lookup=evidence_lookup,
        pdf_pages=pdf_pages,
    )

    if not verified.hypotheses:
        # Cache-authoritative gate dropped everything → abstain to the scaffold.
        return _verified_scaffold()

    # REASON-06 / #30: never claim safety from absence. Model hypotheses get
    # confidence set by derive_confidence_tier (which returns 'high' for any
    # evidence-cited hypothesis), so apply the same missing-data downgrade the
    # static scaffold uses — a med-citing hypothesis is dropped one rung when a
    # safety-critical category (labs/allergies) is absent from the record.
    downgraded = apply_gap_downgrades(
        list(verified.hypotheses), live_gap_fhir_types(list(resources))
    )

    # verify_packet preserves completeness, but the live path swaps in the
    # model's hypotheses + REASONED_SUMMARY over the scaffold, so re-assert the
    # scaffold's completeness to guarantee the "what's missing" view survives.
    return verified.model_copy(
        update={"hypotheses": downgraded, "completeness": list(scaffold.completeness)}
    )
