"""Beers Criteria 2023 lookup for potentially inappropriate medications in adults ≥65.

Purely synchronous; operates on the vendored seeds/beers.json seed. No external
API calls. Age-gated: returns empty results for patients under 65.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.app.dtos import EvidenceSnippet
from backend.app.knowledge.loader import load_beers

_MIN_AGE = 65

# ── Data containers ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BeersMatch:
    rule_id: str
    category: str
    drug_name: str  # normalised patient-medication name that matched
    beers_term: str  # original seed term, incl. dose/formulation qualifier
    recommendation: str
    rationale: str
    quality_of_evidence: str
    strength: str
    snippet: EvidenceSnippet


@dataclass
class BeersResult:
    matches: list[BeersMatch] = field(default_factory=list)
    # Patient drug names for which no Beers rule was found (not flagged as unsafe,
    # just unverified — caller may want to surface coverage gaps).
    unresolved: list[str] = field(default_factory=list)
    snippets: list[EvidenceSnippet] = field(default_factory=list)
    # False only when age was unknown (None): Beers could not be evaluated, so an
    # empty result means "not assessed", NOT "no risk". A genuinely-young patient
    # was assessed (Beers does not apply), so age_known stays True for them.
    age_known: bool = True


# ── Module-level lazy index ────────────────────────────────────────────────

_INDEX: dict[str, list[tuple[str, dict[str, Any]]]] | None = None


def _get_index() -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Build and cache a normalised-name → list[(seed_term, rule)] lookup.

    The seed term is kept alongside each rule so a dose/formulation qualifier
    (e.g. ``aspirin (>325 mg/day)``) survives into the match — ``_normalise``
    strips it only for *matching*, never from the surfaced output.
    """
    global _INDEX  # noqa: PLW0603
    if _INDEX is None:
        data = load_beers()
        idx: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for rule in data["rules"]:
            for drug in rule["drugs"]:
                key = _normalise(drug)
                idx.setdefault(key, []).append((drug, rule))
        _INDEX = idx
    return _INDEX


# ── Helpers ────────────────────────────────────────────────────────────────


def _normalise(name: str) -> str:
    """Lowercase and strip parenthetical qualifiers (e.g. route or dose riders)."""
    return re.sub(r"\s*\(.*?\)", "", name).strip().lower()


# ── Public API ─────────────────────────────────────────────────────────────


def lookup_beers(drug_names: list[str], age_years: int | None) -> BeersResult:
    """Return Beers Criteria matches for *drug_names* in a patient aged *age_years*.

    ``age_years`` is ``int | None`` because the upstream patient record may not
    carry a birth date (``_compute_age_years`` returns ``None`` and the minimised
    patient omits ``ageYears`` entirely). The two empty-result cases are kept
    distinct so absence is never rendered as "no risk":

    * ``age_years is None`` — age unknown, Beers could not be evaluated. Returns
      ``BeersResult(age_known=False)``; the caller must surface this as UNKNOWN.
    * ``age_years < 65`` — patient assessed; Beers does not apply. Returns an
      empty ``BeersResult`` (``age_known=True``); the age gate is explicit and
      not treated as a coverage gap (``unresolved`` stays empty).
    """
    if age_years is None:
        return BeersResult(age_known=False)
    if age_years < _MIN_AGE:
        return BeersResult()

    data = load_beers()
    citation = data["citation"]
    index = _get_index()

    matches: list[BeersMatch] = []
    unresolved: list[str] = []

    for med in drug_names:
        norm = _normalise(med)
        entries = index.get(norm)
        if entries is None:
            unresolved.append(med)
            continue
        for term, rule in entries:
            snippet = EvidenceSnippet(
                id=f"beers:{rule['id']}:{norm}",
                kind="beers_criteria",
                ref=citation,
                label=f"Beers 2023 [{term}] — {rule['category']}: {rule['recommendation']}",
            )
            matches.append(
                BeersMatch(
                    rule_id=rule["id"],
                    category=rule["category"],
                    drug_name=norm,
                    beers_term=term,
                    recommendation=rule["recommendation"],
                    rationale=rule["rationale"],
                    quality_of_evidence=rule["quality_of_evidence"],
                    strength=rule["strength"],
                    snippet=snippet,
                )
            )

    snippets = [m.snippet for m in matches]
    return BeersResult(matches=matches, unresolved=unresolved, snippets=snippets)
