"""Prompt template for the Gemini reasoning call.

Assembles the flattened patient context + evidence cards into a single
prompt that instructs the model to return structured JSON hypotheses
with traceable citations.
"""

from collections.abc import Sequence

from backend.app.knowledge.openfda import EvidenceSnippet

SYSTEM_INSTRUCTION = (
    "You are a clinical reasoning assistant. "
    "Analyse the patient's clinical data and evidence cards below, "
    "then suggest possible links between the patient's symptoms, "
    "conditions, medications, allergies, and procedures.\n\n"
    "## Rules\n"
    "1. ONLY reference facts that are explicitly present in the text below. "
    "Do NOT invent or assume any facts that are not written here.\n"
    "2. Every suggestion MUST cite its sources using the exact tags you see:\n"
    "   - Patient facts use tags like `[MedicationStatement/ms-001]` — "
    "use kind `\"resource\"` and ref `\"MedicationStatement/ms-001\"` (no brackets)\n"
    "   - Evidence cards use their stable IDs like "
    "`openfda:197885:adverse_events:total_count` — "
    "use kind `\"evidence\"` and ref set to the full ID\n"
    "3. Provide a confidence level: `\"high\"`, `\"medium\"`, or `\"low\"`.\n"
    "4. Provide a severity level: `\"critical\"`, `\"serious\"`, `\"moderate\"`, or `\"minor\"`.\n"
    "5. If there is not enough information to form any suggestion, "
    'return `{"hypotheses": []}` — do NOT invent anything.\n\n'
    "## Output format\n"
    "Respond ONLY with a JSON object matching this structure — no other text:\n\n"
    '```json\n'
    '{\n'
    '  "hypotheses": [\n'
    '    {\n'
    '      "title": "Short title describing the suggested link",\n'
    '      "why": "Explanation referencing specific data points from the text",\n'
    '      "severity": "critical|serious|moderate|minor",\n'
    '      "confidence": "high|medium|low",\n'
    '      "citations": [\n'
    '        {"kind": "resource", "ref": "MedicationStatement/ms-001", '
    '"label": "Brief description of the fact"},\n'
    '        {"kind": "evidence", "ref": "openfda:197885:adverse_events:total_count", '
    '"label": "Brief description of the evidence"}\n'
    '      ]\n'
    '    }\n'
    '  ]\n'
    '}\n'
    '```\n\n'
    "Now, respond with ONLY the JSON object."
)


def _format_evidence(evidence: Sequence[EvidenceSnippet]) -> str:
    """Render evidence snippets as a numbered list."""
    if not evidence:
        return "_(no evidence cards available)_"
    lines: list[str] = []
    for i, snippet in enumerate(evidence, 1):
        lines.append(
            f"{i}. [{snippet.id}] ({snippet.kind}) {snippet.label[:200]}"
        )
    return "\n".join(lines)


def build_reasoning_prompt(
    flattened_patient_text: str,
    evidence: Sequence[EvidenceSnippet],
) -> str:
    """Assemble the full prompt for the Gemini reasoning call.

    Parameters
    ----------
    flattened_patient_text : str
        Tagged markdown output from ``flatten_to_tagged_text()``.
        Each data line should start with ``[ResourceType/id]``.
    evidence : Sequence[EvidenceSnippet]
        Evidence cards (e.g. from OpenFDA lookups).

    Returns
    -------
    str
        The complete prompt string ready to send to ``generate_content``.
    """
    evidence_text = _format_evidence(evidence)
    patient_section = f"## Patient Clinical Data\n\n{flattened_patient_text}"
    evidence_section = f"## Evidence Cards\n\n{evidence_text}"

    return (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"{patient_section}\n\n"
        f"{evidence_section}\n\n"
    )
