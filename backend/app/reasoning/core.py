"""Reasoning core: Gemini API call, response parsing, and citation verification.

This module wires together the end-to-end reasoning pipeline:

1. Assemble the prompt via ``prompts.build_reasoning_prompt()``
2. Call Google Gemini with structured JSON output
3. Parse the response into :class:`~backend.app.dtos.Hypothesis` objects
4. Verify that every patient-fact and evidence citation actually resolves
   (REASON-02 deterministic verifier)

Usage
-----
    hypotheses = await run_reasoning(flattened_text, evidence_snippets)
"""

import json
import os
import re
from collections.abc import Sequence
from typing import Any

import httpx
from google.genai import Client, types
from google.genai import errors as genai_errors

from backend.app.dtos import Citation, Hypothesis
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.prompts import build_reasoning_prompt

# ── Configuration ──────────────────────────────────────────────────────────

DEFAULT_MODEL = "gemini-2.5-flash"

# Known citation kinds that the verifier will check.  Any citation whose
# kind is outside this set is silently dropped (anti-hallucination).
_KNOWN_CITATION_KINDS: frozenset[str] = frozenset({"resource", "evidence"})

# Regex to extract ``[ResourceType/id]`` from flattened patient text.
_TAG_RE = re.compile(r"\[([A-Za-z]+/[a-zA-Z0-9_.:-]+)]")

# ── Client factory ─────────────────────────────────────────────────────────


def _get_client() -> Client:
    """Return a synchronous Google GenAI client.

    The API key is read from the ``GOOGLE_GENAI_API_KEY`` environment
    variable at call time.  Raises ``KeyError`` (or the configured
    error handler) when unset.
    """
    api_key = os.environ["GOOGLE_GENAI_API_KEY"]
    return Client(api_key=api_key)


# ── Response parser ────────────────────────────────────────────────────────


def parse_gemini_response(response_text: str) -> list[Hypothesis]:
    """Parse the Gemini JSON response into ``Hypothesis`` objects.

    Parameters
    ----------
    response_text : str
        Raw JSON string returned by the model.

    Returns
    -------
    list[Hypothesis]
        Parsed hypotheses.  Returns an empty list when the response
        contains no hypotheses (valid empty case).

    Raises
    ------
    ValueError
        When the response is not valid JSON or doesn't match the
        expected ``{"hypotheses": [...]}`` envelope.
    """
    if not response_text or not response_text.strip():
        raise ValueError("Gemini returned an empty response")

    try:
        data: dict[str, Any] = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned malformed JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    raw_hypotheses = data.get("hypotheses", [])
    if not isinstance(raw_hypotheses, list):
        raise ValueError(
            f"Expected 'hypotheses' to be a list, " f"got {type(raw_hypotheses).__name__}"
        )

    results: list[Hypothesis] = []
    for i, raw in enumerate(raw_hypotheses):
        if not isinstance(raw, dict):
            continue
        results.append(
            Hypothesis(
                id=f"hyp-{i + 1}",
                title=raw.get("title", ""),
                why=raw.get("why", ""),
                severity=raw.get("severity", "moderate"),
                confidence=raw.get("confidence", "low"),
                citations=[
                    Citation(
                        kind=c.get("kind", ""),
                        ref=c.get("ref", ""),
                        label=c.get("label"),
                    )
                    for c in (raw.get("citations") or [])
                    if isinstance(c, dict)
                ],
            )
        )
    return results


# ── Citation helpers ───────────────────────────────────────────────────────


def _extract_patient_tags(flattened_text: str) -> set[str]:
    """Return every bare ``ResourceType/id`` tag in the flattened text."""
    return set(_TAG_RE.findall(flattened_text))


def _strip_brackets(ref: str) -> str:
    """Remove surrounding ``[`` ``]`` from a tag, if present.

    >>> _strip_brackets("[Condition/c1]")
    'Condition/c1'
    >>> _strip_brackets("Condition/c1")
    'Condition/c1'
    """
    return ref.strip("[]") if ref.startswith("[") else ref


# ── Citation verifier (REASON-02) ──────────────────────────────────────────


def verify_citations(
    hypotheses: list[Hypothesis],
    flattened_text: str,
    evidence_ids: set[str],
) -> list[Hypothesis]:
    """Drop hypotheses whose citations cannot be resolved (REASON-02).

    A citation is resolved when:
    * ``kind == "resource"`` — its ``ref`` (e.g. ``Patient/pat-001``
      or ``[Patient/pat-001]``) exists as a tag in the flattened text.
    * ``kind == "evidence"`` — its ``ref`` matches one of the
      provided *evidence_ids*.
    * Any citation whose ``kind`` is not in the known set is silently
      dropped (anti-hallucination on unknown kinds).

    If **any** verified citation in a hypothesis fails to resolve,
    the entire hypothesis is dropped.

    Parameters
    ----------
    hypotheses : list[Hypothesis]
        Parsed hypotheses from ``parse_gemini_response()``.
    flattened_text : str
        The same text that was passed to the prompt.
    evidence_ids : set[str]
        Set of evidence-snippet IDs that were provided.

    Returns
    -------
    list[Hypothesis]
        Surviving hypotheses.
    """
    if not hypotheses:
        return hypotheses

    patient_tags = _extract_patient_tags(flattened_text)

    verified: list[Hypothesis] = []
    for h in hypotheses:
        # Filter out unknown citation kinds, then check surviving ones.
        known_citations = [c for c in h.citations if c.kind in _KNOWN_CITATION_KINDS]
        valid = True
        for c in known_citations:
            if c.kind == "resource":
                bare_ref = _strip_brackets(c.ref)
                if bare_ref not in patient_tags:
                    valid = False
                    break
            elif c.kind == "evidence":
                if c.ref not in evidence_ids:
                    valid = False
                    break
        if valid and known_citations:
            # Keep only known citations in the output hypothesis
            h.citations = known_citations
            verified.append(h)
    return verified


# ── Top-level reasoning pipeline ───────────────────────────────────────────


async def run_reasoning(
    flattened_text: str,
    evidence: Sequence[EvidenceSnippet],
    *,
    model: str = DEFAULT_MODEL,
) -> list[Hypothesis]:
    """Run the end-to-end Gemini reasoning pipeline.

    1. Build the prompt from patient context + evidence cards.
    2. Call Gemini with ``response_mime_type="application/json"``.
    3. Parse the structured JSON response.
    4. Verify that every citation resolves (REASON-02).
    5. Return the surviving hypotheses.

    If the Gemini API call fails (network error, rate limit, auth failure)
    the error is caught and an empty list is returned — the caller should
    interpret this as "abstention" (REASON-08).

    Parameters
    ----------
    flattened_text : str
        Tagged markdown output from :func:`~backend.app.fhir.flatten.flatten_to_tagged_text`.
    evidence : Sequence[EvidenceSnippet]
        Evidence cards (e.g. from OpenFDA lookups).
    model : str
        Gemini model name (default ``gemini-2.5-flash``).

    Returns
    -------
    list[Hypothesis]
        Verified, citation-gated hypotheses.
    """
    prompt = build_reasoning_prompt(flattened_text, evidence)

    client = _get_client()
    aio = client.aio

    try:
        response = await aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
    except (genai_errors.ClientError, httpx.HTTPStatusError, httpx.RequestError):
        # REASON-08: abstention — cannot produce any hypotheses
        return []

    try:
        hypotheses = parse_gemini_response(response.text)
    except ValueError:
        return []

    evidence_ids = {s.id for s in evidence}
    hypotheses = verify_citations(hypotheses, flattened_text, evidence_ids)

    return hypotheses
