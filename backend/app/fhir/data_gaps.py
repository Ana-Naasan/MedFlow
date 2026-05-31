"""Data-gap tracking for clinical decision support.

Three states (mirroring the flattener's output labels):
  present        — category has documented data from the source
  stated_none    — source explicitly asserts none (e.g. NKA allergy code)
  not_documented — source covers the category but returned nothing

Rules (REASON-05):
  - Never claim safety from absence.  "Not documented" means unknown, not safe.
  - Only emit "stated as none" when a source NKA code actually warrants it.
  - Downgrade hypothesis confidence when a safety-critical category is a gap.
"""

from __future__ import annotations

from typing import Literal

from backend.app.dtos import Hypothesis
from backend.app.fhir.flatten import _is_nka

# ── Category / FHIR type mapping ──────────────────────────────────────────────

# Coverage-dict key → FHIR resource type.
# Keys match the convention used in FetchResult.coverage dicts.
COVERAGE_TO_FHIR: dict[str, str] = {
    "medications": "MedicationStatement",
    "conditions": "Condition",
    "observations": "Observation",
    "allergies": "AllergyIntolerance",
    "procedures": "Procedure",
}

# Safety-critical categories: gaps here mandate a confidence downgrade for any
# drug-related hypothesis because the missing data directly affects assessment.
_SAFETY_CRITICAL_FHIR_TYPES: frozenset[str] = frozenset(
    {
        "AllergyIntolerance",  # unknown allergy → can't rule out contraindications
        "Observation",  # missing labs → can't verify dosing/monitoring
    }
)

_CONFIDENCE_LADDER: list[str] = ["high", "medium", "low"]

CoverageState = Literal["present", "stated_none", "not_documented"]

# ── Public API ────────────────────────────────────────────────────────────────


def coverage_state(fhir_type: str, resources: list[dict]) -> CoverageState:
    """Classify a single FHIR category into one of three states.

    Returns
    -------
    'present'        — one or more non-NKA records exist
    'stated_none'    — all AllergyIntolerance records carry an NKA code
    'not_documented' — no records of this type exist in the input
    """
    items = [r for r in resources if r.get("resourceType") == fhir_type]
    if not items:
        return "not_documented"
    if fhir_type == "AllergyIntolerance" and all(_is_nka(fhir_type, r) for r in items):
        return "stated_none"
    return "present"


def compute_data_gaps(
    resources: list[dict],
    coverage: dict[str, dict[str, bool]],
) -> list[str]:
    """Return human-readable gap strings for categories covered-but-not-returned.

    A category produces a gap when:
    - The source claims to cover it (coverage[cat]['requested'] == True)
    - No data was returned (state == 'not_documented')

    NKA allergy entries are NOT gaps — the source explicitly asserts none.
    Categories the source doesn't cover produce no gap (out of scope).

    The output list is sorted for determinism.
    """
    gaps: list[str] = []
    for cat, flags in coverage.items():
        if not flags.get("requested"):
            continue
        fhir_type = COVERAGE_TO_FHIR.get(cat)
        if fhir_type is None:
            continue
        state = coverage_state(fhir_type, resources)
        if state == "not_documented":
            label = cat.replace("_", " ").capitalize()
            gaps.append(f"{label} not documented — source returned nothing for this category")
    return sorted(gaps)


def gap_fhir_types(
    resources: list[dict],
    coverage: dict[str, dict[str, bool]],
) -> set[str]:
    """Return the FHIR types a source covers but returned nothing for.

    Routes real connector coverage through :func:`coverage_state` and the
    ``COVERAGE_TO_FHIR`` map, so a production downgrade set is derived from the
    actual record rather than a hardcoded literal — and a ``COVERAGE_TO_FHIR``
    mapping regression surfaces here. Pass the result to
    :func:`apply_gap_downgrades`.
    """
    out: set[str] = set()
    for cat, flags in coverage.items():
        if not flags.get("requested"):
            continue
        fhir_type = COVERAGE_TO_FHIR.get(cat)
        if fhir_type is None:
            continue
        if coverage_state(fhir_type, resources) == "not_documented":
            out.add(fhir_type)
    return out


def downgrade_for_gaps(
    hypothesis: Hypothesis,
    gap_fhir_types: set[str],
) -> Hypothesis:
    """Downgrade confidence by one step when a safety-critical category is absent.

    Applies only when:
    - At least one safety-critical type (AllergyIntolerance, Observation) is missing
    - The hypothesis cites at least one MedicationStatement

    Downgrade ladder: 'high' → 'medium', 'medium' → 'low'.  Already 'low' or
    an unknown confidence string → unchanged.

    Returns the same object (identity) when no downgrade is needed.
    """
    if not gap_fhir_types.intersection(_SAFETY_CRITICAL_FHIR_TYPES):
        return hypothesis
    if not _cites_medications(hypothesis):
        return hypothesis
    try:
        idx = _CONFIDENCE_LADDER.index(hypothesis.confidence)
    except ValueError:
        return hypothesis  # unknown confidence level → leave untouched
    if idx >= len(_CONFIDENCE_LADDER) - 1:
        return hypothesis  # already at 'low'
    return Hypothesis(
        id=hypothesis.id,
        title=hypothesis.title,
        why=hypothesis.why,
        severity=hypothesis.severity,
        confidence=_CONFIDENCE_LADDER[idx + 1],
        citations=list(hypothesis.citations),
        group=hypothesis.group,
    )


def apply_gap_downgrades(
    hypotheses: list[Hypothesis],
    gap_fhir_types: set[str],
) -> list[Hypothesis]:
    """Apply ``downgrade_for_gaps`` to every hypothesis in the list."""
    return [downgrade_for_gaps(h, gap_fhir_types) for h in hypotheses]


# ── Internal helpers ──────────────────────────────────────────────────────────


def _cites_medications(hypothesis: Hypothesis) -> bool:
    return any(
        c.kind == "resource" and c.ref.startswith("MedicationStatement/")
        for c in hypothesis.citations
    )
