"""Decision-packet orchestration: the production caller for the reasoning core.

The EVAL-REVIEW's BLOCKER #1 was that ``run_reasoning`` had no production
caller — the "primary online guardrail" ran on zero requests. This module is
that caller. It flattens the patient's FHIR resources, runs the Gemini reasoning
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

from collections.abc import Sequence

from backend.app.dtos import DecisionPacket
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
        # it abstains (citation-free); otherwise completeness is restored (the
        # verifier rebuilds the packet without that field).
        checked = verify_packet(
            scaffold,
            resource_lookup=resource_lookup,
            evidence_lookup=evidence_lookup,
            pdf_pages=pdf_pages,
        )
        if not checked.hypotheses:
            return checked
        return checked.model_copy(update={"completeness": list(scaffold.completeness)})

    try:
        hypotheses = await run_reasoning(flattened, evidence, model=model)
    except KeyError:
        # _get_client reads GOOGLE_GENAI_API_KEY at call time and raises KeyError
        # (unset or blank) OUTSIDE run_reasoning's try/except — treat as abstention.
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

    # verify_packet rebuilds the packet without the completeness field; restore it
    # so the "what's missing" view survives the live path.
    return verified.model_copy(update={"completeness": list(scaffold.completeness)})
