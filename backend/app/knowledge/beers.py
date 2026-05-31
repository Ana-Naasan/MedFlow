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


# ── Module-level lazy index ────────────────────────────────────────────────

_INDEX: dict[str, list[dict[str, Any]]] | None = None


def _get_index() -> dict[str, list[dict[str, Any]]]:
    """Build and cache a normalised-name → list[rule] lookup."""
    global _INDEX  # noqa: PLW0603
    if _INDEX is None:
        data = load_beers()
        idx: dict[str, list[dict[str, Any]]] = {}
        for rule in data["rules"]:
            for drug in rule["drugs"]:
                key = _normalise(drug)
                idx.setdefault(key, []).append(rule)
        _INDEX = idx
    return _INDEX


# ── Helpers ────────────────────────────────────────────────────────────────


def _normalise(name: str) -> str:
    """Lowercase and strip parenthetical qualifiers (e.g. route or dose riders)."""
    return re.sub(r"\s*\(.*?\)", "", name).strip().lower()


# ── Public API ─────────────────────────────────────────────────────────────


def lookup_beers(drug_names: list[str], age_years: int) -> BeersResult:
    """Return Beers Criteria matches for *drug_names* in a patient aged *age_years*.

    Returns an empty ``BeersResult`` immediately when ``age_years < 65``; the
    age gate is explicit and not treated as a coverage gap (``unresolved`` stays
    empty).
    """
    if age_years < _MIN_AGE:
        return BeersResult()

    data = load_beers()
    citation = data["citation"]
    index = _get_index()

    matches: list[BeersMatch] = []
    unresolved: list[str] = []

    for med in drug_names:
        norm = _normalise(med)
        rules = index.get(norm)
        if rules is None:
            unresolved.append(med)
            continue
        for rule in rules:
            snippet = EvidenceSnippet(
                id=f"beers:{rule['id']}:{norm}",
                kind="beers_criteria",
                ref=citation,
                label=f"Beers 2023 — {rule['category']}: {rule['recommendation']}",
            )
            matches.append(
                BeersMatch(
                    rule_id=rule["id"],
                    category=rule["category"],
                    drug_name=norm,
                    recommendation=rule["recommendation"],
                    rationale=rule["rationale"],
                    quality_of_evidence=rule["quality_of_evidence"],
                    strength=rule["strength"],
                    snippet=snippet,
                )
            )

    snippets = [m.snippet for m in matches]
    return BeersResult(matches=matches, unresolved=unresolved, snippets=snippets)
