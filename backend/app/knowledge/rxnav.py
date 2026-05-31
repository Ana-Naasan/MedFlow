"""Bridge drug names to RxNorm codes via the free NIH RxNav REST API.

Every medication name fed to the reasoning core is first resolved through
this module.  When a drug cannot be matched the caller is notified via
``DrugResolution.resolved == False`` (flagged, never silently dropped).

If the overall input is too thin (fewer than half of names resolve) a
``low_confidence_note`` is set on the report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

# ── Public API ─────────────────────────────────────────────────────────────

BASE_URL = "https://rxnav.nlm.nih.gov/REST"

# When fewer than this fraction of drug names resolve, the report carries
# a low-confidence note.
_THIN_INPUT_THRESHOLD = 0.5


@dataclass
class DrugResolution:
    """Result of resolving a single drug name through RxNav."""

    input_name: str
    rxcui: str | None = None
    name: str | None = None
    ingredient_rxcui: str | None = None
    atc_codes: list[str] = field(default_factory=list)
    resolved: bool = False
    match_quality: str = "failed"  # "exact" | "approximate" | "failed"


@dataclass
class DrugResolutionReport:
    """Aggregated result of resolving multiple drug names."""

    resolutions: list[DrugResolution] = field(default_factory=list)
    low_confidence_note: str | None = None

    def __post_init__(self) -> None:
        if self.low_confidence_note is None and self.total_count > 0:
            ratio = self.resolved_count / self.total_count
            if ratio < _THIN_INPUT_THRESHOLD:
                self.low_confidence_note = (
                    f"limited input — low confidence: only "
                    f"{self.resolved_count}/{self.total_count} drugs resolved"
                )
        if self.low_confidence_note is None and self.total_count == 0:
            self.low_confidence_note = (
                "limited input — low confidence: no drugs provided"
            )

    @property
    def total_count(self) -> int:
        return len(self.resolutions)

    @property
    def resolved_count(self) -> int:
        return sum(1 for r in self.resolutions if r.resolved)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.resolutions if not r.resolved)


# ── Shared HTTP client ─────────────────────────────────────────────────────

_client_instance: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Return a shared module-level HTTP client (reused across calls)."""
    global _client_instance
    if _client_instance is None:
        _client_instance = httpx.Client(base_url=BASE_URL, timeout=10.0)
    return _client_instance


# ── Internal helpers ───────────────────────────────────────────────────────


def _lookup_name(name: str) -> str | None:
    """Call ``REST/rxcui.json?name=...`` and return the first RxCUI, or
    ``None`` when nothing matches.  Network errors are caught and return
    ``None`` so the caller can fall back to approximate match."""
    try:
        resp = _get_client().get("/rxcui.json", params={"name": name})
        if resp.status_code != 200:
            return None
        body = resp.json()
        ids = body.get("idGroup", {}).get("rxnormId", [])
        return ids[0] if ids else None
    except httpx.RequestError:
        return None


def _approximate_match(name: str) -> str | None:
    """Call ``REST/approximateTerm.json?term=...`` and return the top
    candidate's RxCUI, or ``None``.  Network errors are caught and return
    ``None``."""
    try:
        resp = _get_client().get(
            "/approximateTerm.json", params={"term": name, "maxEntries": 1}
        )
        if resp.status_code != 200:
            return None
        body = resp.json()
        candidates = body.get("approximateGroup", {}).get("candidate", [])
        if not candidates:
            return None
        return candidates[0].get("rxcui") or None
    except httpx.RequestError:
        return None


def _fetch_properties(rxcui: str) -> list[dict[str, Any]]:
    """Call ``allProperties.json`` and return the propConcept list.

    Returns an empty list when the endpoint fails, returns a non-200
    status, or when ``propConcept`` is ``null``.
    """
    try:
        resp = _get_client().get(
            f"/rxcui/{rxcui}/allProperties.json",
            params={"prop": "NAMES,CODES"},
        )
        if resp.status_code != 200:
            return []
        body = resp.json()
        prop_group = body.get("propConceptGroup") or {}
        props = prop_group.get("propConcept") or []
        # Defensive: skip non-dict entries in the array
        return [p for p in props if isinstance(p, dict)]
    except httpx.RequestError:
        return []


def _fetch_ingredient(rxcui: str) -> str | None:
    """Call ``REST/rxcui/{rxcui}/related.json?tty=IN`` and return the
    first ingredient RxCUI, or ``None``."""
    try:
        resp = _get_client().get(f"/rxcui/{rxcui}/related.json", params={"tty": "IN"})
        if resp.status_code != 200:
            return None
        body = resp.json()
        groups = body.get("relatedGroup", {}).get("conceptGroup", [])
        for g in groups:
            if g.get("tty") == "IN":
                props = g.get("conceptProperties") or []
                if props:
                    return props[0].get("rxcui") or None
        return None
    except httpx.RequestError:
        return None


# ── Public functions ───────────────────────────────────────────────────────


def resolve_drug(name: str) -> DrugResolution:
    """Resolve a single drug name to its RxNorm codes.

    First tries an exact match, then falls back to the approximate-term
    endpoint (handles typos).  When no match is found the result has
    ``resolved=False`` and ``match_quality="failed"``.

    Parameters
    ----------
    name : str
        Drug name (e.g. ``"metformin"``, ``"Lisinopril 5 MG Oral Tablet"``).

    Returns
    -------
    DrugResolution
    """
    if not name:
        return DrugResolution(input_name=name, resolved=False, match_quality="failed")

    # Try exact lookup first
    rxcui = _lookup_name(name)

    quality = "exact"
    if rxcui is None:
        # Fallback: approximate match (handles typos / minor misspellings)
        rxcui = _approximate_match(name)
        quality = "approximate"

    if rxcui is None:
        return DrugResolution(input_name=name, resolved=False, match_quality="failed")

    # Fetch extra properties (ATC codes, canonical name)
    props = _fetch_properties(rxcui)
    atc_codes = [
        p.get("propValue", "")
        for p in props
        if p.get("propName") == "ATC"
    ]
    display_name = (
        next(
            (
                p.get("propValue", "")
                for p in props
                if p.get("propCategory") == "NAMES"
            ),
            None,
        )
        or name
    )

    # Fetch ingredient RxCUI (for downstream DDInter bridging)
    ingredient_rxcui = _fetch_ingredient(rxcui)

    return DrugResolution(
        input_name=name,
        rxcui=rxcui,
        name=display_name,
        ingredient_rxcui=ingredient_rxcui,
        atc_codes=atc_codes,
        resolved=True,
        match_quality=quality,
    )


def resolve_drugs(names: list[str]) -> DrugResolutionReport:
    """Resolve multiple drug names and produce a report.

    When fewer than half of the names resolve successfully the report
    carries a ``low_confidence_note`` (handled automatically by
    ``DrugResolutionReport.__post_init__``).

    Parameters
    ----------
    names : list[str]
        One or more drug names.

    Returns
    -------
    DrugResolutionReport
    """
    resolutions = [resolve_drug(n) for n in names]
    return DrugResolutionReport(resolutions=resolutions)
