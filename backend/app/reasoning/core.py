"""Reasoning core: Gemini API call, response parsing, and citation verification.

This module wires together the end-to-end reasoning pipeline:

1. Assemble the prompt via ``prompts.build_reasoning_prompt()``
2. Call Google Gemini with structured JSON output
3. Parse the response into :class:`~backend.app.dtos.Hypothesis` objects
4. Verify every patient-fact and evidence citation resolves AND every
   citation kind is known — an unknown kind taints the whole hypothesis,
   not just that one citation (REASON-02 / #75 per-clause grounding).
5. Apply the deterministic output-language gate (#75) — drop hypotheses
   whose ``title``/``why`` contains causal attribution, drug directives,
   or dose directives. Mirrors the fail-closed posture of the citation
   gate so the invariant doesn't depend on model compliance.

Usage
-----
    hypotheses = await run_reasoning(flattened_text, evidence_snippets)
"""

import json
import os
import re
from collections.abc import Sequence
from typing import Any, NamedTuple

import httpx
from google.genai import Client, types
from google.genai import errors as genai_errors
from pydantic import ValidationError

from backend.app.dtos import Citation, Hypothesis
from backend.app.knowledge.openfda import EvidenceSnippet
from backend.app.reasoning.prompts import build_reasoning_prompt

# ── Configuration ──────────────────────────────────────────────────────────

DEFAULT_MODEL = "gemini-2.5-flash"

# Known citation kinds that the verifier will check.  Any citation whose
# kind is outside this set is treated as a verification failure for the
# WHOLE hypothesis (#75 per-clause grounding) — the unknown citation likely
# backs a fabricated claim in the free-text ``why``/``title``.
_KNOWN_CITATION_KINDS: frozenset[str] = frozenset({"resource", "evidence"})

# Regex to extract ``[ResourceType/id]`` from flattened patient text.
# Anchored to line start (MULTILINE): the flattener emits each real tag as the
# leading token of its line, so anchoring prevents a ``[Type/id]`` substring
# embedded in source-controlled free-text (a med name, an Observation value)
# from being treated as a resolvable patient tag (forged-citation defence).
_TAG_RE = re.compile(r"^\[([A-Za-z]+/[a-zA-Z0-9_.:-]+)]", re.MULTILINE)

# Deterministic output-language guard (AI-SPEC §5 dim 3; EVAL-REVIEW BLOCKER).
# The prompt INSTRUCTS associational phrasing — this ENFORCES it: any surfaced
# title/why asserting causation or a prescriptive drug directive is dropped,
# mirroring the fail-closed posture of the citation gate so the non-negotiable
# output-language invariant ("may be associated", never "caused by"/"stop drug X")
# does not depend on model compliance.
#
# Phrase set is intentionally curated to avoid false-positives on valid
# associational text. In particular:
#   - bare "increase"/"decrease" is NEVER matched (would flag "increased risk",
#     "increase in INR"); only the dose-directive form below is matched
#   - bare "stop"/"start" is NEVER matched (would flag "stop the bleeding",
#     "start of symptoms"); only the verbed forms ("stop taking",
#     "should stop", "recommend stopping") are matched
#   - "cause" / "cause of" without "caused by"/"causes" is NOT matched (would
#     flag "the cause is unclear", "uncertain cause")
#
# Editing this set is a clinical/UX judgement call — see #75 for the broader
# curation review.
_FORBIDDEN_LANGUAGE = re.compile(
    # ── Causal attribution ──────────────────────────────────────────────
    r"\bcaused\s+by\b" r"|\bcauses\b" r"|\bdue\s+to\b"
    # ── Direct drug directives ──────────────────────────────────────────
    r"|\bdiscontinue\b" r"|\bstop\s+taking\b" r"|\bmust\s+(?:stop|start)\b"
    # ── Recommendation-form directives (#75 broadening) ─────────────────
    # "recommend stopping X" / "recommends discontinuing X" / etc.
    r"|\brecommend(?:s|ed|ing)?\s+(?:stopping|discontinuing|starting|switching|changing)\b"
    # "should stop/start/discontinue/switch X" (verbed — won't catch
    # "stop the bleeding")
    r"|\bshould\s+(?:stop|discontinue|start|switch)\b"
    # "should not take/use/continue/start X"
    r"|\bshould\s+not\s+(?:take|use|continue|start)\b"
    # "advise against/stopping/discontinuing/starting"
    r"|\b(?:we\s+|strongly\s+)?advise\s+(?:against|stopping|discontinuing|starting)\b"
    # ── Dose directives ─────────────────────────────────────────────────
    # Narrow "increase/decrease/reduce the dose/dosage/frequency" — does
    # NOT match bare "increased risk" / "decrease in eGFR".
    r"|\b(?:increase|decrease|reduce)\s+the\s+(?:dose|dosage|frequency)\b",
    re.IGNORECASE,
)


def _has_forbidden_language(h: Hypothesis) -> bool:
    """True if the hypothesis's surfaced prose (title/why) violates the
    associational-only output-language invariant."""
    return bool(_FORBIDDEN_LANGUAGE.search(f"{h.title}\n{h.why}"))


# ── Client factory ─────────────────────────────────────────────────────────


def _get_client() -> Client:
    """Return a synchronous Google GenAI client.

    The API key is read from the ``GOOGLE_GENAI_API_KEY`` environment
    variable at call time.  An unset OR blank key raises ``KeyError`` — a
    uniform abstention signal the caller treats as "cannot reason".  (A blank
    key must not reach ``Client(api_key="")``, which raises ``ValueError`` and
    would escape the caller's abstention handling → HTTP 500.)
    """
    api_key = os.environ.get("GOOGLE_GENAI_API_KEY", "")
    if not api_key.strip():
        raise KeyError("GOOGLE_GENAI_API_KEY")
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
        try:
            hypothesis = Hypothesis(
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
        except (ValidationError, TypeError):
            # One drifting field type (LLMs occasionally emit null/number/array
            # for a field) drops only THIS hypothesis, not the whole batch — the
            # good, fully-citable hypotheses still reach verification. Fails closed.
            continue
        results.append(hypothesis)
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


# ── Symptom ↔ MedDRA reaction match (REASON-05) ─────────────────────────────

# Curated symptom→synonym bridge: maps a canonical symptom bucket to the
# alternate strings clinicians / FAERS MedDRA terms commonly use for it. The
# bridge is INTENTIONALLY conservative and clinician-reviewable — it is a
# string-matching aid, NOT a clinical ontology, and does not bypass the
# citation verifier (every surfaced match is gated downstream like any other
# evidence reference). Extend with clinical judgement (see PRD §12 REASON-05).
# NOTE on term selection: synonyms are matched as case-insensitive *substrings*
# (so "bleed" reaches "bleeding"/"bleeds"). Bare ambiguous stems that collide
# with benign clinical vitals are deliberately excluded — e.g. "blood" is NOT a
# synonym because it fires on "Systolic Blood Pressure"/"Blood pressure panel"
# Observations, injecting a spurious "Blood Pressure ↔ hemorrhage" candidate
# (the bleeding bucket is reached via "bleed"/"bleeding"/"hemorrhage" instead).
_SYMPTOM_SYNONYMS: dict[str, list[str]] = {
    "bleeding": ["hemorrhage", "haemorrhage", "bleed", "bruising", "bruise"],
    "nausea": ["nauseous", "vomiting", "emesis", "sick to stomach"],
    "fatigue": ["tired", "weakness", "lethargy", "exhaustion"],
    "pain": ["ache", "discomfort", "soreness"],
    "dizziness": ["vertigo", "lightheaded", "dizzy", "syncope"],
    "rash": ["urticaria", "hives", "skin reaction", "dermatitis"],
    "swelling": ["edema", "oedema", "swollen"],
    "confusion": ["cognitive", "disorientation", "mental status"],
}

# Observation lines in the flattened context carry the patient's symptom /
# observation free-text. Anchored to line start (MULTILINE), mirroring _TAG_RE,
# so only the flattener's real leading tag is treated as a patient symptom — an
# embedded "[Observation/...]" substring inside source-controlled free text
# cannot forge a symptom line.
_OBSERVATION_LINE_RE = re.compile(r"^\[Observation/[a-zA-Z0-9_.:-]+]\s*(.+)$", re.MULTILINE)


class SymptomReactionMatch(NamedTuple):
    """A curated link between patient symptom text and a FAERS reaction term.

    Attributes
    ----------
    symptom_text:
        The Observation line's free-text (the patient-reported symptom).
    reaction_term:
        The synonym/term that matched within an evidence snippet's label.
    evidence_id:
        The stable id of the evidence snippet the term was found in — the same
        id the citation verifier resolves against (matches do NOT bypass it).
    """

    symptom_text: str
    reaction_term: str
    evidence_id: str


def _extract_observation_texts(flattened_text: str) -> list[str]:
    """Return the free-text of every ``[Observation/...]`` line, in order."""
    return [m.strip() for m in _OBSERVATION_LINE_RE.findall(flattened_text)]


def _candidate_terms(symptom_text: str) -> list[str]:
    """Build the case-insensitive search terms for one symptom line.

    For every canonical bucket whose key OR one of its synonyms appears in the
    symptom text, the canonical key and all its synonyms become candidate terms
    to look for in the evidence labels. This is what lets a symptom worded as
    "tired" reach the FAERS term "fatigue" (and vice-versa).
    """
    lowered = symptom_text.lower()
    terms: list[str] = []
    seen: set[str] = set()
    for canonical, synonyms in _SYMPTOM_SYNONYMS.items():
        bucket = [canonical, *synonyms]
        if any(word in lowered for word in bucket):
            for word in bucket:
                if word not in seen:
                    seen.add(word)
                    terms.append(word)
    return terms


def match_symptoms_to_reactions(
    flattened_text: str,
    evidence: Sequence[EvidenceSnippet],
) -> list[SymptomReactionMatch]:
    """Bridge patient symptom text to FAERS/MedDRA reaction terms (REASON-05).

    Each ``[Observation/...]`` line's free-text is matched, case-insensitively
    and via the curated synonym bridge, against the reaction text carried in the
    evidence snippets openFDA returned. A match is recorded as
    ``(symptom_text, reaction_term, evidence_snippet_id)``.

    The match is a *prompt aid only*: it surfaces a candidate link for the model
    to reason about, but the surviving hypotheses are still gated by the citation
    verifier — a match never bypasses ``verify_citations`` (REASON-02).

    Parameters
    ----------
    flattened_text:
        Tagged markdown from ``flatten_to_tagged_text`` (Observation lines hold
        the patient's symptoms / observations).
    evidence:
        Evidence snippets whose ``label`` text carries reaction terms (e.g.
        "Most-reported reactions: nausea, bleeding...").

    Returns
    -------
    list[SymptomReactionMatch]
        One entry per (symptom line, reaction term, evidence snippet) match.
        Deduplicated; empty when nothing links.
    """
    observations = _extract_observation_texts(flattened_text)
    if not observations:
        return []

    matches: list[SymptomReactionMatch] = []
    seen: set[tuple[str, str, str]] = set()
    for symptom_text in observations:
        terms = _candidate_terms(symptom_text)
        if not terms:
            continue
        for snippet in evidence:
            label_lower = snippet.label.lower()
            for term in terms:
                if term in label_lower:
                    key = (symptom_text, term, snippet.id)
                    if key not in seen:
                        seen.add(key)
                        matches.append(SymptomReactionMatch(symptom_text, term, snippet.id))
    return matches


def _format_symptom_matches(matches: Sequence[SymptomReactionMatch]) -> str:
    """Render symptom↔reaction matches as a prompt context block (or empty str).

    Returns an empty string when there are no matches so the caller can omit the
    section entirely rather than injecting an empty heading.
    """
    if not matches:
        return ""
    lines = [f'- "{m.symptom_text}" ↔ "{m.reaction_term}" ({m.evidence_id})' for m in matches]
    rendered = "\n".join(lines)
    return (
        "## Symptom–reaction matches (curated, candidate links — verify before relying)\n\n"
        "Each line pairs a patient symptom/observation with a reaction term found in "
        "the evidence cards above. These are candidate associations only; cite the "
        "evidence card by its id and use associational phrasing.\n\n"
        f"{rendered}"
    )


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

    Per-clause prose grounding (#75 hardening)
    ------------------------------------------
    Any citation whose ``kind`` is not in the known set is now treated as a
    **verification failure for the whole hypothesis** — not silently filtered.
    Rationale: an unknown-kind citation is a strong tell of hallucination, and
    the hypothesis's free-text ``why``/``title`` may well be relying on the
    fabricated source. Surfacing only the structured-citation subset while the
    prose still asserts the unsupported claim is worse than dropping the
    whole entry. Previously such hypotheses survived on their remaining known
    citations; now they're dropped.

    If **any** citation (known or unknown) fails to resolve, the entire
    hypothesis is dropped.

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
        Surviving hypotheses (all citations verified, all kinds known).
    """
    if not hypotheses:
        return hypotheses

    patient_tags = _extract_patient_tags(flattened_text)

    verified: list[Hypothesis] = []
    for h in hypotheses:
        if not h.citations:
            continue
        # Per-clause grounding (#75): an unknown citation kind taints the
        # whole hypothesis — its prose may rely on the fabricated source.
        if any(c.kind not in _KNOWN_CITATION_KINDS for c in h.citations):
            continue
        valid = True
        for c in h.citations:
            if c.kind == "resource":
                bare_ref = _strip_brackets(c.ref)
                if bare_ref not in patient_tags:
                    valid = False
                    break
            elif c.kind == "evidence":
                if c.ref not in evidence_ids:
                    valid = False
                    break
        if valid:
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
    4. Verify every citation resolves AND every citation kind is known —
       a single unknown-kind citation drops the whole hypothesis as a
       fabrication tell (REASON-02 / #75 per-clause grounding).
    5. Apply the deterministic output-language gate: drop any hypothesis
       whose ``title``/``why`` contains causal attribution ("caused by",
       "due to"), drug directives ("discontinue", "stop taking", "should
       stop"), or dose directives ("increase the dose"). Curated to avoid
       false-positives on valid associational text like "increased risk"
       (#75 hardening of AI-SPEC §5 dim 3).
    6. Return the surviving hypotheses.

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

    # REASON-05: surface curated symptom↔reaction matches as additional context.
    # This only informs the model; the citation verifier below still gates every
    # surviving hypothesis, so a match cannot bypass the safety bar.
    matches = match_symptoms_to_reactions(flattened_text, evidence)
    match_block = _format_symptom_matches(matches)
    if match_block:
        # Re-assert the JSON-only directive AFTER the appended block so the last
        # thing the model reads is the output contract, not the candidate links.
        prompt = f"{prompt}{match_block}\n\nNow, respond with ONLY the JSON object.\n"

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
    except (genai_errors.APIError, httpx.HTTPStatusError, httpx.RequestError):
        # REASON-08: abstention — cannot produce any hypotheses.
        # Catch the base genai APIError (not just ClientError): 5xx maps to the
        # SIBLING ServerError (e.g. 503 "model overloaded", the most common
        # transient Gemini failure), which must abstain, not crash.
        return []

    try:
        hypotheses = parse_gemini_response(response.text)
    except ValueError:
        return []

    evidence_ids = {s.id for s in evidence}
    hypotheses = verify_citations(hypotheses, flattened_text, evidence_ids)

    # Deterministic output-language gate: drop any hypothesis whose prose asserts
    # causation or a prescriptive directive (don't trust the prompt alone).
    hypotheses = [h for h in hypotheses if not _has_forbidden_language(h)]

    return hypotheses
