"""DDInter drug-drug interaction lookup (#22).

Given a list of :class:`DrugResolution` objects (from :mod:`rxnav`), find every
interacting pair documented in the vendored DDInter CSV and emit a structured
:class:`DDInterInteraction` per hit.

DDInter is keyed by drug name (e.g. "Warfarin", "Acetylsalicylic acid"), not
RxCUI, so this module bridges from the RxNorm-shaped inputs by trying, in
order:

  1. The original ``input_name`` (case-insensitive).
  2. The RxNav-resolved canonical ``name``.
  3. A small vendored synonym map for known RxNorm ↔ DDInter name divergences
     (e.g. RxNorm "aspirin" ↔ DDInter "Acetylsalicylic acid").

Matches via the synonym map are flagged ``unsure=True`` — they're never
dropped, but the reasoning core should hedge accordingly. Approximate RxNav
matches (the typo-correction path) also flag the result as unsure.

The synonym map is intentionally narrow: it only covers the demo-critical
drugs where the RxNorm preferred-term and DDInter preferred-term diverge. A
class-level (ATC) bridge is tracked as future work.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Literal, cast

from backend.app.knowledge.loader import load_ddinter
from backend.app.knowledge.rxnav import DrugResolution

Severity = Literal["Minor", "Moderate", "Major"]
MatchMethod = Literal["input_name", "rxnav_name", "synonym"]

# Valid DDInter severity levels. Rows whose level is outside this set are
# treated as malformed and skipped at index-build time, so the ``Severity``
# typing of stored rows is a checked invariant rather than a blind assumption.
_VALID_LEVELS: frozenset[str] = frozenset({"Minor", "Moderate", "Major"})


# ── Vendored synonym map: RxNorm preferred-term → DDInter preferred-term ─────
#
# Keys are lowercased RxNorm names; values are the EXACT casing used in the
# vendored DDInter CSV. Synonym-resolved matches are flagged unsure (see
# below) so the reasoning core can hedge.
_RXNORM_TO_DDINTER_SYNONYMS: dict[str, str] = {
    "aspirin": "Acetylsalicylic acid",
    "acetaminophen": "Paracetamol",
    "tylenol": "Paracetamol",
}


@dataclass(frozen=True, slots=True)
class DDInterInteraction:
    """A single interaction hit between two of the patient's resolved drugs.

    ``drug_a`` / ``drug_b`` carry the DDInter-canonical name (so downstream
    citations show the chemical name, not the RxNorm everyday term).
    """

    drug_a: str
    drug_b: str
    level: Severity
    ddinter_id_a: str
    ddinter_id_b: str
    match_method_a: MatchMethod
    match_method_b: MatchMethod
    unsure: bool
    evidence_id: str
    snippet: str


# ── Index (lazy, module-level) ────────────────────────────────────────────────

# Adjacency: lowercased name → { lowercased partner name → row tuple }.
# Row tuple = (drug_a_original, drug_b_original, level, id_a, id_b).
_RowTuple = tuple[str, str, str, str, str]
_INDEX: dict[str, dict[str, _RowTuple]] | None = None


def _build_index() -> dict[str, dict[str, _RowTuple]]:
    idx: dict[str, dict[str, _RowTuple]] = {}
    for row in load_ddinter():
        a_orig, b_orig = row["drug_a"], row["drug_b"]
        a_key, b_key = a_orig.strip().lower(), b_orig.strip().lower()
        if not a_key or not b_key or a_key == b_key:
            continue
        if row["level"] not in _VALID_LEVELS:
            continue  # malformed severity → skip (keeps Severity typing honest)
        info: _RowTuple = (a_orig, b_orig, row["level"], row["ddinter_id_a"], row["ddinter_id_b"])
        idx.setdefault(a_key, {})[b_key] = info
        idx.setdefault(b_key, {})[a_key] = info
    return idx


def _index() -> dict[str, dict[str, _RowTuple]]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def clear_cache() -> None:
    """Force the next ``find_interactions`` call to rebuild the index."""
    global _INDEX
    _INDEX = None


# ── Per-drug key selection ────────────────────────────────────────────────────


def _pick_key(
    r: DrugResolution, index: dict[str, dict[str, _RowTuple]]
) -> tuple[MatchMethod, str] | None:
    """Pick the best DDInter-index key for this resolution.

    Tries input_name → RxNav name → synonym map. Returns ``None`` when the
    resolution didn't resolve or no candidate key appears in the index.
    """
    if not r.resolved:
        return None
    if r.input_name:
        key = r.input_name.strip().lower()
        if key in index:
            return ("input_name", key)
    if r.name:
        key = r.name.strip().lower()
        if key in index:
            return ("rxnav_name", key)
    for src in (r.input_name, r.name):
        if not src:
            continue
        canonical = _RXNORM_TO_DDINTER_SYNONYMS.get(src.strip().lower())
        if canonical is None:
            continue
        key = canonical.strip().lower()
        if key in index:
            return ("synonym", key)
    return None


def _stable_evidence_id(a: str, b: str) -> str:
    """Order-independent, lowercase, hyphen-joined id (e.g. ``ddinter-aspirin-warfarin``)."""
    return "ddinter-" + "-".join(sorted([a.strip().lower(), b.strip().lower()]))


# ── Public API ────────────────────────────────────────────────────────────────


def find_interactions(resolutions: list[DrugResolution]) -> list[DDInterInteraction]:
    """Return every DDInter interaction for the resolved drug pairs.

    Each pair is unsure when (a) either side was an approximate RxNav match,
    or (b) either side was bridged via the synonym map.

    Results are sorted by ``evidence_id`` for determinism.
    """
    index = _index()
    keyed: list[tuple[DrugResolution, MatchMethod, str]] = []
    for r in resolutions:
        picked = _pick_key(r, index)
        if picked is None:
            continue
        method, key = picked
        keyed.append((r, method, key))

    found: list[DDInterInteraction] = []
    for (ra, ma, ka), (rb, mb, kb) in combinations(keyed, 2):
        row = index.get(ka, {}).get(kb)
        if row is None:
            continue
        a_orig, b_orig, level, id_a, id_b = row
        # drug_a/drug_b + their ids come from CSV row order; ma/mb follow the
        # resolution (combinations) order. Align each match method to the drug
        # it actually resolved so match_method_a always describes drug_a, even
        # when the patient's input order is the reverse of the CSV row order.
        if a_orig.strip().lower() == ka:
            method_a, method_b = ma, mb
        else:  # a_orig corresponds to the kb side
            method_a, method_b = mb, ma
        unsure = (
            ra.match_quality == "approximate"
            or rb.match_quality == "approximate"
            or ma == "synonym"
            or mb == "synonym"
        )
        found.append(
            DDInterInteraction(
                drug_a=a_orig,
                drug_b=b_orig,
                level=cast(Severity, level),  # checked in _build_index
                ddinter_id_a=id_a,
                ddinter_id_b=id_b,
                match_method_a=method_a,
                match_method_b=method_b,
                unsure=unsure,
                evidence_id=_stable_evidence_id(a_orig, b_orig),
                snippet=(f"DDInter: {a_orig} + {b_orig} → {level} interaction."),
            )
        )
    found.sort(key=lambda i: i.evidence_id)
    return found
