"""Bridge drug names to RxNorm codes via the free NIH RxNav REST API.

Intended to be called by the reasoning pipeline before DDInter lookups
(#22).  When a drug cannot be matched the result has ``resolved=False``
(flagged, never silently dropped).  Network errors are also flagged
via ``network_error=True`` so the caller can distinguish "not found"
from "API unavailable."

Every HTTP helper catches ``httpx.RequestError`` and returns ``None`` /
``[]`` — transport failures never raise.  The caller sees
``network_error=True`` on the final result and can act accordingly.

This module uses a **shared synchronous** ``httpx.Client`` (module-level).
The sibling ``openfda.py`` is async — they serve different callers.
Call :func:`close_client` to release the connection pool when the
application shuts down.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

BASE_URL = "https://rxnav.nlm.nih.gov/REST"
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
    network_error: bool = False  # True when a transport error occurred


@dataclass
class DrugResolutionReport:
    """Aggregated result of resolving multiple drug names."""

    resolutions: list[DrugResolution] = field(default_factory=list)
    low_confidence_note: str | None = None
    network_error: bool = False  # True when any resolution had a network error

    def __post_init__(self) -> None:
        if self.low_confidence_note is None and self.total_count > 0:
            ratio = self.resolved_count / self.total_count
            if ratio < _THIN_INPUT_THRESHOLD:
                self.low_confidence_note = (
                    f"limited input — low confidence: only "
                    f"{self.resolved_count}/{self.total_count} drugs resolved"
                )
        if self.low_confidence_note is None and self.total_count == 0:
            self.low_confidence_note = "limited input — low confidence: no drugs provided"

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


def close_client() -> None:
    """Close the shared HTTP client, if one exists, and reset for reuse."""
    global _client_instance
    if _client_instance is not None:
        _client_instance.close()
        _client_instance = None


# ── Internal helpers ───────────────────────────────────────────────────────

# Sentinel returned by helpers to indicate a transport error (as opposed to a
# genuine empty result).  The resolve_drug function checks for this.
_NETWORK_ERROR = object()


def _lookup_name(name: str) -> str | None:
    """Return the first RxCUI for *name*, or ``None``.

    Returns ``_NETWORK_ERROR`` when a transport error occurs.
    """
    try:
        resp = _get_client().get("/rxcui.json", params={"name": name})
        if resp.status_code != 200:
            return None
        body = resp.json()
        ids = body.get("idGroup", {}).get("rxnormId", [])
        return ids[0] if ids else None
    except httpx.RequestError:
        return _NETWORK_ERROR  # type: ignore[return-value]


def _approximate_match(name: str) -> str | None:
    """Return the top approximate RxCUI for *name*, or ``None``.

    Returns ``_NETWORK_ERROR`` when a transport error occurs.
    """
    try:
        resp = _get_client().get("/approximateTerm.json", params={"term": name, "maxEntries": 1})
        if resp.status_code != 200:
            return None
        body = resp.json()
        candidates = body.get("approximateGroup", {}).get("candidate", [])
        if not candidates:
            return None
        return candidates[0].get("rxcui") or None
    except httpx.RequestError:
        return _NETWORK_ERROR  # type: ignore[return-value]


def _fetch_properties(rxcui: str) -> list[dict[str, Any]] | object:
    """Return the propConcept list for *rxcui*, ``[]`` on failure.

    Returns ``_NETWORK_ERROR`` when a transport error occurs (as opposed to
    a non-200 response, which yields ``[]``).
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
        return [p for p in props if isinstance(p, dict)]
    except httpx.RequestError:
        return _NETWORK_ERROR


def _fetch_ingredient(rxcui: str) -> str | None | object:
    """Return the first ingredient RxCUI for *rxcui*, or ``None``.

    Returns ``_NETWORK_ERROR`` when a transport error occurs.
    """
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
        return _NETWORK_ERROR


# ── Public functions ───────────────────────────────────────────────────────


def resolve_drug(name: str) -> DrugResolution:
    """Resolve a single drug name to its RxNorm codes.

    First tries an exact match, then falls back to the approximate-term
    endpoint (handles typos).  When no match is found the result has
    ``resolved=False`` and ``match_quality="failed"``.

    When a transport error occurs at *any* stage, ``network_error=True``
    is set on the result so the caller can distinguish "not found" from
    "API unavailable."
    """
    if not name:
        return DrugResolution(input_name=name, resolved=False, match_quality="failed")

    rxcui = _lookup_name(name)

    quality = "exact"
    net_err = False
    if rxcui is _NETWORK_ERROR:
        net_err = True
        rxcui = None
    if rxcui is None:
        rxcui = _approximate_match(name)
        if rxcui is _NETWORK_ERROR:
            net_err = True
            rxcui = None
        quality = "approximate"

    if rxcui is None:
        return DrugResolution(input_name=name, resolved=False, match_quality="failed", network_error=net_err)

    props = _fetch_properties(rxcui)
    if props is _NETWORK_ERROR:
        net_err = True
        props = []

    atc_codes = [
        v for v in (p.get("propValue", "") for p in props if p.get("propName") == "ATC")
        if v.strip()
    ]

    # Pick the NAME entry (not a synonym or tall-man form).
    display_name = next(
        (p.get("propValue", "") for p in props if p.get("propName") == "NAME"),
        None,
    )
    if not display_name:
        display_name = next(
            (p.get("propValue", "") for p in props if p.get("propCategory") == "NAMES"),
            None,
        )
    if not display_name:
        display_name = name

    ingredient_rxcui = _fetch_ingredient(rxcui)
    if ingredient_rxcui is _NETWORK_ERROR:
        net_err = True
        ingredient_rxcui = None

    return DrugResolution(
        input_name=name,
        rxcui=rxcui,
        name=display_name,
        ingredient_rxcui=ingredient_rxcui,
        atc_codes=atc_codes,
        resolved=True,
        match_quality=quality,
        network_error=net_err,
    )


def resolve_drugs(names: list[str]) -> DrugResolutionReport:
    """Resolve multiple drug names and produce a report.

    When fewer than half of the names resolve successfully the report
    carries a ``low_confidence_note``.  If any resolution experienced
    a network error the report's ``network_error`` is ``True``.
    """
    resolutions = [resolve_drug(n) for n in names]
    return DrugResolutionReport(
        resolutions=resolutions,
        network_error=any(r.network_error for r in resolutions),
    )
