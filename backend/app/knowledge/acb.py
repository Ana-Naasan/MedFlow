"""Anticholinergic Cognitive Burden (ACB) score computation.

Operates on the vendored seeds/acb.json seed. No external API calls, no age
gate. When *age_years* is provided and ≥ 65, score-3 snippet labels include an
elevated-risk rider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from backend.app.dtos import EvidenceSnippet
from backend.app.knowledge.loader import load_acb

# ── Data containers ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AcbMatch:
    drug_name: str  # normalised patient-medication name that matched
    acb_score: int  # 1 | 2 | 3
    snippet: EvidenceSnippet


@dataclass
class AcbResult:
    total_score: int = 0
    matches: list[AcbMatch] = field(default_factory=list)
    # Patient drug names for which no ACB entry was found.
    unresolved: list[str] = field(default_factory=list)
    snippets: list[EvidenceSnippet] = field(default_factory=list)


# ── Module-level lazy index ────────────────────────────────────────────────

_INDEX: dict[str, dict[str, Any]] | None = None


def _get_index() -> dict[str, dict[str, Any]]:
    """Build and cache a normalised-name → drug-entry lookup."""
    global _INDEX  # noqa: PLW0603
    if _INDEX is None:
        data = load_acb()
        _INDEX = {_normalise(d["name"]): d for d in data["drugs"]}
    return _INDEX


# ── Helpers ────────────────────────────────────────────────────────────────


def _normalise(name: str) -> str:
    """Lowercase and strip parenthetical qualifiers."""
    return re.sub(r"\s*\(.*?\)", "", name).strip().lower()


def _score_label(drug_name: str, score: int, age_years: int | None) -> str:
    base = f"ACB score {score}/3 — {drug_name}"
    if score == 3 and age_years is not None and age_years >= 65:
        return base + " (elevated cognitive risk in adults ≥65)"
    return base


# ── Public API ─────────────────────────────────────────────────────────────


def lookup_acb(drug_names: list[str], age_years: int | None = None) -> AcbResult:
    """Compute ACB burden for *drug_names*.

    *age_years* is optional. When provided and ≥ 65, score-3 snippet labels are
    enriched with an elevated-risk note. No hard age gate — ACB applies to all
    patients.
    """
    if not drug_names:
        return AcbResult()

    data = load_acb()
    citation = data["citation"]
    index = _get_index()

    matches: list[AcbMatch] = []
    unresolved: list[str] = []

    for med in drug_names:
        norm = _normalise(med)
        entry = index.get(norm)
        if entry is None:
            unresolved.append(med)
            continue
        score = entry["acb_score"]
        snippet = EvidenceSnippet(
            id=f"acb:{norm}:score_{score}",
            kind="acb_score",
            ref=citation,
            label=_score_label(entry["name"], score, age_years),
        )
        matches.append(AcbMatch(drug_name=entry["name"], acb_score=score, snippet=snippet))

    total = sum(m.acb_score for m in matches)
    snippets: list[EvidenceSnippet] = [m.snippet for m in matches]

    if total > 0:
        sorted_names = ",".join(sorted(m.drug_name for m in matches))
        snippets.append(
            EvidenceSnippet(
                id=f"acb:total:{sorted_names}",
                kind="acb_total",
                ref=citation,
                label=f"Total ACB score: {total} ({len(matches)} drug(s))",
            )
        )

    return AcbResult(
        total_score=total,
        matches=matches,
        unresolved=unresolved,
        snippets=snippets,
    )
